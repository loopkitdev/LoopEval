"""The pump and the infusion site: what reaches the tissue, given what the controller commanded.

LoopEval's trace records COMMANDED delivery (already pulse-quantized by the engine for patch pumps,
ice L25). This layer decides what the body gets, minute by minute (COMPONENTS §E):

  E2 site life        absorption speed rises over a site's life (Swan 2009: day 4 acts ~18 min
                      earlier than day 1) → abs_mult 0.9 at insertion → 1.15 by day 4 [derived]
  E3 site change      delivery stops while the old site is removed and the new one primed
                      (minutes; person trait), the new site starts slow
  E4 failing site     a share of sites fail partway through their life: the fraction of delivered
                      insulin that is absorbed decays (occlusion / leak / kink) until the person
                      changes it (eda L52: early changes are a quarter; glucose climbs 6–12 h first
                      with delivery flat; Kanapka 2022: 3.3% of sets end with > 250 for ~5 h)
  E5–E8 delivery accuracy, stiction, cannula leakage, occlusion alarms: evidence/06 (pending review);
                      hooks exist here, all OFF until sized.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DAY = 1440.0


@dataclass
class SiteTraits:
    p_fail: float = 0.15            # share of sites that fail before the planned change [J; eda L52 bound: early changes 25%]
    fail_floor: float = 0.3         # absorbed fraction a failed site decays to [J]
    fail_tau: float = 240.0         # min
    change_gap: float = 15.0        # min with no delivery during a change [J]
    abs_new: float = 0.9            # absorption speed at insertion (relative)
    abs_slope: float = 0.0625       # per day, to 1.15 at day 4 [derived from Swan 2009]


class Pump:
    def __init__(self, traits: SiteTraits, rng: np.random.Generator):
        self.t = traits
        self.rng = rng
        self.site_start = -rng.uniform(0, 2) * DAY
        self.gap_until = -1.0
        self.fail_at = None
        self._arm_failure(self.site_start)
        self.queue: list[tuple[float, float, float]] = []    # (start, end, units) commanded, not yet delivered
        self.delivered = 0.0
        self.commanded = 0.0
        self.log = []

    def _arm_failure(self, start: float):
        self.fail_at = start + self.rng.uniform(0.5, 3.0) * DAY if self.rng.random() < self.t.p_fail else None

    def change_site(self, m: float):
        self.site_start = m + self.t.change_gap
        self.gap_until = m + self.t.change_gap
        self._arm_failure(self.site_start)
        self.log.append((m, "site_change"))

    def command(self, start: float, end: float, units: float, bolus: bool = False):
        """A commanded dose (minutes); basal spread over [start, end), a bolus delivered in its first minute."""
        if units <= 0: return
        self.commanded += units
        self.queue.append((start, max(end, start + 1.0), units, bolus))

    def site_state(self, m: float) -> tuple[float, float]:
        """(absorption speed multiplier, absorbed fraction) of the current site."""
        age = max(0.0, (m - self.site_start) / DAY)
        absm = self.t.abs_new + self.t.abs_slope * min(age, 4.0)
        bio = 1.0
        if self.fail_at is not None and m > self.fail_at:
            bio = self.t.fail_floor + (1 - self.t.fail_floor) * math.exp(-(m - self.fail_at) / self.t.fail_tau)
        return absm, bio

    def failing(self, m: float) -> bool:
        return self.fail_at is not None and m > self.fail_at

    def deliver(self, m: float) -> float:
        """Units leaving the pump into the site during minute [m, m+1)."""
        if m < self.gap_until:
            # delivery suspended during a site change: commanded insulin in this window is lost
            self.queue = [q for q in self.queue if q[1] > m + 1]
            return 0.0, 0.0
        u = 0.0; ub = 0.0
        keep = []
        for (s, e, units, bolus) in self.queue:
            if e <= m:
                continue
            lo, hi = max(s, m), min(e, m + 1)
            if hi > lo:
                if bolus: ub += units * (hi - lo) / (e - s)
                else: u += units * (hi - lo) / (e - s)
            if e > m + 1: keep.append((s, e, units, bolus))
        self.queue = keep
        self.delivered += u + ub
        return u, ub
