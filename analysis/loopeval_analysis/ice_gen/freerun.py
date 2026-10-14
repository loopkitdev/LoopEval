"""Scheduled sampling for the background-ICE path (ice LESSONS 42).

Every input built from the person's own recent background ICE (CGM level and trend, 30-min projection, heading-low,
minutes below 70, the 30-min background-ICE EMA) carries real, smooth ICE in training but the model's own draws in
generation, and the model read its near-independent draws as a volatile state (30-65% wider predicted spread in closed
loop). Here, after a teacher-forced warm-up, the model runs step by step on its own sampled background ICE: glucose is the
real glucose plus the running difference between its draws and the real background ICE (insulin, meals and actions stay
as recorded), the derived inputs are rebuilt from it exactly as the plant builds them, and the loss is the density of the
REAL next background ICE under the prediction made from those own-draw inputs.
"""
from __future__ import annotations

import torch

from .dataset import ICE_SCALE
from .dataset_v3 import EMA_A, TREND_SLOTS
from .model_v2 import mdn_nll, mdn_sample

LOW, HIGH = 40.0, 400.0


def freerun_bgice_loss(net, X, Y, person, features, targets, burn):
    """X [B, W, F], Y [B, W, T] (one training window), person [B]. Teacher-forced through `burn` steps, then free-running.
    Returns the mean NLL of the real next background ICE over the free-running steps where it is known."""
    F = {f: i for i, f in enumerate(features)}
    ib = targets.index("bgice")
    B, W, _ = X.shape
    _, h = net(X[:, :burn], person)
    bg_real = X[..., F["bg"]] * 100                                   # forward-filled CGM, mg/dL
    hist = [bg_real[:, burn - k] for k in range(TREND_SLOTS + 4, 0, -1)]   # generated glucose, last few steps (starts real)
    off = torch.zeros(B, device=X.device)                             # generated minus real glucose, mg/dL
    ema = X[:, burn - 1, F["bgice_ema"]] * ICE_SCALE if "bgice_ema" in F else None
    nll = []
    for t in range(burn, W - 1):
        x = X[:, t].clone()
        g = (bg_real[:, t] + off).clamp(LOW, HIGH)
        x[:, F["bg"]] = g / 100
        if "bg_trend" in F:
            tr = (g - hist[-TREND_SLOTS]) / (TREND_SLOTS * 5)
            x[:, F["bg_trend"]] = tr / 2
            if "bg_pred30" in F:
                p = (g + 30 * tr).clamp(40, 400)
                x[:, F["bg_pred30"]] = p / 100
                x[:, F["heading_low"]] = ((p < 70) | ((g < 80) & (tr < 0))).float()
            if "low30" in F:
                x[:, F["low30"]] = torch.stack([(v < 70).float() for v in hist[-5:] + [g]], 0).sum(0) * 5 / 30
        if ema is not None:
            x[:, F["bgice_ema"]] = ema / ICE_SCALE
        if "bgice_ok" in F:
            x[:, F["bgice_ok"]] = 1.0
        if "bg_ok" in F:
            x[:, F["bg_ok"]] = 1.0
        out, h = net(x[:, None], person, h)
        p = out["bgice"][:, 0]
        y = Y[:, t, ib]                                               # real background ICE of the next slot (scaled)
        ok = torch.isfinite(y)
        if ok.any():
            nll.append(mdn_nll(p[ok], y[ok], net.K_ICE))
        with torch.no_grad():
            d = mdn_sample(p, net.K_ICE)                              # the model's own draw for the next slot
            dy = torch.where(ok, d - torch.nan_to_num(y), torch.zeros_like(d)) * ICE_SCALE
            off = off + dy * 5 / 60
            if ema is not None:
                ema = torch.where(torch.isfinite(ema), ema + EMA_A * (d * ICE_SCALE - ema), d * ICE_SCALE)
            hist = hist[1:] + [g]
    return torch.cat(nll).mean() if nll else torch.zeros((), device=X.device)
