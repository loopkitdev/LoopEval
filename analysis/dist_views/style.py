"""Shared look and shared loading for the distribution views."""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                        # noqa: E402
import pandas as pd                       # noqa: E402

RUN_NAME = "2026-08-25-distributions"


def _runs_root() -> Path:
    """Where run outputs live — deliberately not inside the checkout.

    They are large (>100 GB across the project) and git-ignored, so duplicating
    them per worktree is not an option. Resolution order: an explicit
    LOOPEVAL_RUNS, the shared store beside the data cache, then this checkout's
    own runs/ (which may be a symlink to either).
    """
    env = os.environ.get("LOOPEVAL_RUNS")
    if env:
        return Path(env).expanduser()
    for cand in (Path("~/.loop-eval/runs").expanduser(),
                 Path(__file__).resolve().parents[2] / "runs"):
        if (cand / RUN_NAME).is_dir():
            return cand
    return Path("~/.loop-eval/runs").expanduser()


OUT = _runs_root() / RUN_NAME
FIG = OUT / "figs"

SURFACE = "#fcfcfb"
INK, INK2, MUTED, RULE = "#0f1419", "#48545f", "#87929e", "#e6e5e0"
ACCENT, WARM, COOL, GREEN = "#eb6834", "#b98900", "#3b6ea5", "#1baf7a"

# Categorical colours by algorithm / behaviour group
GROUP_COLOR = {
    "non-announcer": "#3b6ea5",
    "moderate announcer": "#1baf7a",
    "heavy announcer": "#eb6834",
    "oref/Trio": "#8b5cf6",
    "": "#87929e",
}


# ── records that must be cut short, with the reason ───────────────────────────
# p03 wears TWO CGMs concurrently from 2026-06-03. The upload interleaves two
# independent sensors sitting a median 14 mg/dL apart, so consecutive samples
# alternate between them: the increment's lag-1 autocorrelation goes to -0.95
# and its SD from 6.3 to 29.4 mg/dL. Cadence detection also misreads the merged
# stream as 4 min, which silently yields ZERO valid runs. Only the
# single-sensor period is usable. This is the only such record in the cohort
# (screened on: fraction of sub-2-min gaps, and the median |Δbg| across them —
# a genuine fast sensor shows ~1 mg/dL there, two sensors show ~14).
WINDOW_OVERRIDE: dict[str, tuple[str | None, str | None]] = {
    "p03": (None, "2026-06-03"),
}


def clip_window(alias: str, obj):
    """Trim a time-indexed Series/DataFrame to the alias's usable window."""
    w = WINDOW_OVERRIDE.get(alias)
    if w is None or len(obj) == 0:
        return obj
    lo, hi = w
    idx = obj.index
    tz = getattr(idx, "tz", None)
    def _t(x):
        t = pd.Timestamp(x)
        return t.tz_localize("UTC").tz_convert(tz) if tz is not None else t
    m = np.ones(len(idx), dtype=bool)
    if lo is not None:
        m &= np.asarray(idx >= _t(lo))
    if hi is not None:
        m &= np.asarray(idx < _t(hi))
    return obj[m]


def cohort(stratum: str = "core") -> pd.DataFrame:
    """The people a view describes.

    Two strata live in cohort.csv. **core** is hash-ordered and matches the donor
    pool it was drawn from, so it is what the study's figures describe. The
    **hands-off** stratum is deliberately over-sampled — few carb entries, little
    manual bolusing, lower time in range — because the hash-ordered sample
    reached almost nobody there. Pooling them silently would break the
    representativeness claim in view 00, so the default is core only; pass
    "hands-off" or "all" to reach the rest.
    """
    c = pd.read_csv(OUT / "cohort.csv")
    if "stratum" not in c.columns:
        return c
    ho = c["stratum"].eq("hands-off")
    if stratum == "core":                      # off-target exports belong to neither
        return c[c["stratum"].eq("core")].reset_index(drop=True)
    if stratum == "core":
        return c[~ho].reset_index(drop=True)
    if stratum == "hands-off":
        return c[ho].reset_index(drop=True)
    if stratum == "all":
        return c
    raise ValueError(f"unknown stratum {stratum!r} — core, hands-off or all")


def load(alias: str) -> pd.DataFrame:
    return clip_window(alias, pd.read_pickle(OUT / "panels" / f"{alias}.pkl"))


def load_all(aliases=None) -> dict[str, pd.DataFrame]:
    co = cohort()
    aliases = aliases if aliases is not None else list(co["alias"])
    return {a: load(a) for a in aliases}


def group_of(row) -> str:
    """Behaviour group for colouring. Unknown (no cohort row) is "", not a
    different controller — the two must never be conflated."""
    algo = row.get("algo") if hasattr(row, "get") else row["algo"]
    if not isinstance(algo, str):
        return ""
    if algo != "Loop":
        return "oref/Trio"
    return row["archetype"] if isinstance(row["archetype"], str) else ""


def color_for(co: pd.DataFrame, alias: str) -> str:
    """Behaviour-group colour, grey for anyone the cohort does not describe.

    Some views legitimately cover more people than the four-stream cohort — a
    glucose-only statistic has no carb history to classify by. An unknown alias
    is grey, never a colour asserting a group it was never assigned (lesson 20).
    """
    r = co[co["alias"] == alias]
    return GROUP_COLOR.get(group_of(r.iloc[0]), MUTED) if len(r) else MUTED


def axes(ax, *, grid=True):
    ax.set_facecolor(SURFACE)
    if grid:
        ax.grid(True, color=RULE, lw=0.7)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#d5d4cd")
    ax.tick_params(colors=INK2, labelsize=8.5)
    return ax


def figure(nrows=1, ncols=1, figsize=(13, 8), **kw):
    fig, ax = plt.subplots(nrows, ncols, figsize=figsize, **kw)
    fig.patch.set_facecolor(SURFACE)
    for a in (ax.ravel() if hasattr(ax, "ravel") else [ax]):
        axes(a)
    return fig, ax


def title(fig, text, sub=None, y=0.985):
    fig.suptitle(text, fontsize=15, color=INK, x=0.012, ha="left", y=y,
                 weight="bold")
    if sub:
        fig.text(0.012, y - 0.038, sub, fontsize=10, color=INK2, ha="left",
                 va="top", linespacing=1.45)


def _check_titles(fig, name):
    """Warn when a panel title runs past its panel, into a neighbour, or under
    the figure's heading.

    Panel titles are written by hand and the panels get narrower every time a
    figure gains a column, so titles silently overrun. Note WHERE the title
    lives: every title in this study is `loc="left"`, and matplotlib keeps a
    left-aligned title on `ax._left_title`, not on `ax.title` — reading only
    `ax.get_title()` made this whole check a no-op that reported nothing for
    months while collisions shipped.
    """
    fig.canvas.draw()
    head = [t for t in ([fig._suptitle] if fig._suptitle else []) + list(fig.texts)
            if t.get_text()]
    head_boxes = [h.get_window_extent() for h in head]
    boxes = []
    for ax in fig.get_axes():
        for artist in (getattr(ax, "_left_title", None), ax.title,
                       getattr(ax, "_right_title", None)):
            if artist is None or not artist.get_text():
                continue
            t = artist.get_text()
            tb = artist.get_window_extent()
            ab = ax.get_window_extent()
            # A title wider than its panel is only a defect if it reaches
            # something: the gap between panels is there to be used. Flag it
            # when it lands on a neighbouring panel, and say by how much.
            over = tb.width - ab.width
            hit = [o for o in fig.get_axes() if o is not ax
                   and tb.overlaps(o.get_window_extent())]
            if hit:
                print(f"  ! {name}: title reaches into the panel next door "
                      f"({over:.0f}px past its own) — {t[:52]!r}")
            if tb.x1 > fig.bbox.x1 - 2:
                print(f"  ! {name}: title runs off the right edge — {t[:52]!r}")
            if any(tb.overlaps(hb) for hb in head_boxes):
                print(f"  ! {name}: title runs under the figure heading — {t[:52]!r}")
            boxes.append((tb, t))
    for i, (b1, t1) in enumerate(boxes):
        for b2, t2 in boxes[i + 1:]:
            if b1.overlaps(b2):
                print(f"  ! {name}: titles collide — {t1[:34]!r} / {t2[:34]!r}")


def save(fig, name, tight=None, check=True):
    FIG.mkdir(parents=True, exist_ok=True)
    if tight:
        fig.subplots_adjust(**tight)
    if check:
        _check_titles(fig, name)
    fig.savefig(FIG / f"{name}.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {name}.png")


def kde(x, grid, bw=None):
    """Light Gaussian KDE without a scipy dependency."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 10:
        return np.zeros_like(grid)
    if bw is None:
        bw = 1.06 * x.std() * len(x) ** (-1 / 5.0)
    bw = max(bw, 1e-6)
    # Bin first so this stays O(n + grid*bins) on 100k-row panels. Bin over the
    # DATA range, not the grid range — clipping to the grid piles every outlier
    # into the edge bin and makes the tail curl upward.
    lo, hi = float(x.min()), float(x.max())
    if hi <= lo:
        hi = lo + 1e-6
    cnt, edges = np.histogram(x, bins=1024, range=(lo, hi))
    centers = 0.5 * (edges[:-1] + edges[1:])
    d = (grid[:, None] - centers[None, :]) / bw
    w = np.exp(-0.5 * d ** 2) * cnt[None, :]
    dens = w.sum(axis=1) / (len(x) * bw * np.sqrt(2 * np.pi))
    return dens


def strip_kde(ax, values, colors, *, fmt="{:.2f}", note=None, note_x=None,
              note_va="center", seed=7, pad=0.12):
    """Where a per-person statistic sits ACROSS people, on one axis.

    A density curve filling the panel, one dot per person jittered underneath
    it, the median as a full-height line and p10-p90 as a bar. This is the form
    to reach for whenever the question is "what does this number look like over
    the cohort" — a labelled bar per person stops being readable past ~30 and
    the shape of the population is the point anyway. Per-person values belong
    in the ledger table, not on an axis.

    Returns (p10, median, p90).
    """
    import numpy as np
    values = np.asarray(values, dtype=float)
    v = values[np.isfinite(values)]
    if not len(v):
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    lo, med, hi = np.percentile(v, [10, 50, 90])
    span = max(v.max() - v.min(), 1e-9)
    gx = np.linspace(v.min() - pad * span, v.max() + pad * span, 240)
    gy = kde(v, gx)
    gy = gy / max(gy.max(), 1e-12)
    ax.fill_between(gx, 0, gy, color=COOL, alpha=0.16, lw=0, zorder=1)
    ax.plot(gx, gy, color=COOL, lw=1.5, alpha=0.7, zorder=2)
    ax.scatter(values, -0.13 - rng.uniform(0, 0.14, len(values)), s=24, c=colors,
               alpha=0.7, lw=0, zorder=3)
    ax.plot([lo, hi], [-0.34, -0.34], color=INK, lw=2.2, alpha=0.35, zorder=3,
            solid_capstyle="round")
    ax.plot([med, med], [-0.40, 1.02], color=INK, lw=2.0, zorder=4)
    if note is None:
        note = (f"median {fmt.format(med)}\n"
                f"p10-p90 {fmt.format(lo)} to {fmt.format(hi)}")
    if note:
        x = med + 0.04 * span if note_x is None else note_x
        ha = "left" if note_x is None else "right"
        ax.text(x, 0.62, note, fontsize=8.5, color=INK, ha=ha, va=note_va,
                linespacing=1.5, zorder=5)
    ax.set_ylim(-0.46, 1.26)
    ax.set_yticks([])
    return (lo, med, hi)


def order_by(co: pd.DataFrame, col: str, ascending=False) -> list[str]:
    return list(co.sort_values(col, ascending=ascending)["alias"])


def datasets():
    """Rebuild the Dataset list (aliases only) so a view can reach raw inputs."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_bld", str(Path(__file__).resolve().parent / "build.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from loopeval_analysis import dists as D
    out = {d.alias: d for d in D.bddp_datasets(m.BDDP_ROOT)}
    # The wide cohort's own four-stream exports, tagged so no figure pools
    # them silently with the individually-validated donors.
    import os as _os
    if _os.path.isdir(m.WIDE_ROOT):
        out.update({d.alias: d for d in D.bddp_datasets(m.WIDE_ROOT, source="wide")})
    # The hands-off stratum. Reachable here so its raw samples can be analysed;
    # membership in a FIGURE is decided by cohort(), which is core by default.
    if _os.path.isdir(m.HANDSOFF_ROOT):
        out.update({d.alias: d
                    for d in D.bddp_datasets(m.HANDSOFF_ROOT, source="handsoff")})
    for alias, host in m.ns_sites():
        try:
            out[alias] = D.ns_dataset(alias, host)
        except Exception:
            pass
    return out


_RAW_CACHE: dict = {}


def raw_runs(alias: str, minlen: int = 12):
    """Runs of consecutive RAW CGM samples at the sensor's own cadence.

    Returns ``(runs, cadence_min)``. Cadence is detected per dataset — not every
    sensor reports every 5 minutes; at least one of these streams is 1-minute —
    so lags must be expressed in MINUTES and converted, never assumed to be
    five minutes per step.

    Every autocorrelation, structure function and increment-shape statistic
    must come from here rather than from the 5-minute panel. The panel linearly
    interpolates onto a fixed grid, and interpolation is a moving average: it
    inflates the lag-1 autocorrelation of the increment and hides measurement
    noise, which is exactly what those statistics are measuring. Use the panel
    only where alignment with insulin requires a common grid.
    """
    import numpy as np
    if alias in _RAW_CACHE:
        return _RAW_CACHE[alias]
    from loopeval_analysis import dists as D
    ds = datasets()[alias]
    raw = clip_window(alias, D._load_glucose(ds.glucose_path))
    dt = raw.index.to_series().diff().dt.total_seconds() / 60.0
    cadence = float(np.round(dt.median() * 2) / 2)          # to the half minute
    cadence = max(cadence, 0.5)
    ok = ((dt >= 0.8 * cadence) & (dt <= 1.2 * cadence)).to_numpy()
    v = raw.to_numpy()
    out, start = [], 0
    for i in range(1, len(v)):
        if not ok[i]:
            if i - start >= minlen:
                out.append(v[start:i])
            start = i
    if len(v) - start >= minlen:
        out.append(v[start:])
    out = [r for r in out if r.size >= minlen]
    _RAW_CACHE[alias] = (out, cadence)
    return _RAW_CACHE[alias]


def raw_lag(alias: str, minutes: float) -> int:
    """How many native samples correspond to `minutes` for this dataset."""
    _, cad = raw_runs(alias)
    return max(int(round(minutes / cad)), 1)


def raw_delta(alias: str, minutes: float = 5.0):
    """Pooled differences over `minutes`, from raw samples at native cadence."""
    import numpy as np
    rs, _ = raw_runs(alias)
    k = raw_lag(alias, minutes)
    d = [r[k:] - r[:-k] for r in rs if len(r) > k]
    return np.concatenate(d) if d else np.array([])


def raw_step_series(alias: str):
    """Runs of native-cadence FIRST DIFFERENCES, for autocorrelation work."""
    import numpy as np
    rs, _ = raw_runs(alias)
    return [np.diff(r) for r in rs if len(r) > 3]


def representative(co: pd.DataFrame, n: int = 12, key: str = "tir",
                   seed: int = 0) -> list[str]:
    """A stratified representative sample of aliases for line-per-person panels.

    At 70+ people one line per person is unreadable. Instead draw everyone as a
    faint background and colour this sample. It is stratified two ways so it
    covers the cohort rather than being random: seats are shared across the
    behaviour groups in proportion to their size (at least one each), and within
    a group people are taken at evenly spaced quantiles of `key`, so the sample
    spans the range from best to worst rather than clustering at the median.
    Deterministic, so the same people appear in every figure.
    """
    import numpy as np
    d = co.copy()
    d["grp"] = d.apply(group_of, axis=1)
    groups = d.groupby("grp").size().sort_values(ascending=False)
    # at least two per group so range WITHIN a group is visible; proportional above that
    seats = {g: max(2, int(round(n * c / len(d)))) for g, c in groups.items()}
    diff = n - sum(seats.values())               # settle to exactly n on the largest group
    seats[groups.index[0]] = max(2, seats[groups.index[0]] + diff)
    out = []
    for g, k in seats.items():
        sub = d[d.grp == g].sort_values(key)
        if k >= len(sub):
            out += list(sub["alias"]); continue
        qs = np.linspace(0, 1, k + 2)[1:-1]
        idx = sorted({int(round(q * (len(sub) - 1))) for q in qs})
        while len(idx) < k:                       # collisions on tiny groups
            idx.append(min(idx[-1] + 1, len(sub) - 1)); idx = sorted(set(idx))
        out += list(sub["alias"].iloc[idx[:k]])
    return out


def draw_lines(ax, co, aliases, curve, *, sample=None, lw=1.4, bg_lw=0.7,
               bg_alpha=0.18, alpha=0.9, **kw):
    """Draw `curve(alias) -> (x, y)` for everyone faintly, then the sample in colour.

    Returns the sample so a caller can annotate it.
    """
    sample = list(sample) if sample is not None else representative(co)
    keep = set(sample)
    for a in aliases:
        if a in keep:
            continue
        xy = curve(a)
        if xy is None:
            continue
        ax.plot(*xy, color=MUTED, lw=bg_lw, alpha=bg_alpha, zorder=1, **kw)
    for a in sample:
        if a not in set(aliases):
            continue
        xy = curve(a)
        if xy is None:
            continue
        ax.plot(*xy, color=color_for(co, a), lw=lw, alpha=alpha, zorder=3, **kw)
    return sample


_SAMPLE_CACHE: dict = {}


def sample_for(co: pd.DataFrame, n: int = 12) -> list[str]:
    """The representative sample for this cohort, computed once."""
    key = (tuple(co["alias"]), n)
    if key not in _SAMPLE_CACHE:
        _SAMPLE_CACHE[key] = representative(co, n=n)
    return _SAMPLE_CACHE[key]


def line_style(co: pd.DataFrame, alias: str, lw: float = 1.5,
               alpha: float = 0.9) -> dict:
    """Line kwargs for a per-person curve: coloured if in the representative
    sample, faint grey otherwise. Drop-in for `color=..., lw=..., alpha=...`."""
    if alias in set(sample_for(co)):
        return dict(color=color_for(co, alias), lw=lw, alpha=alpha, zorder=3)
    return dict(color=MUTED, lw=0.7, alpha=0.16, zorder=1)
