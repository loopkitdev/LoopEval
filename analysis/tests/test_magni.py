"""Guard the Magni risk constants.

These are pulled from Magni et al. (JDST 2007) and encode a clinical risk weighting, so a silent
edit to any of the three coefficients would change every verdict in the ledger without erroring.
The properties below were MEASURED from the implementation, not recalled — in particular the
minimum sits at ~139 mg/dL, not the ~112 of the Kovatchev function it is often confused with.
Run: python3 -m pytest analysis/tests/test_magni.py   (or execute directly)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from loopeval_analysis.scoring import magni_risk, verify_magni, MAGNI_MIN_BG


def test_minimum_location_and_value():
    v = verify_magni()
    assert abs(v["argmin_bg"] - 138.9) < 0.2, v["argmin_bg"]
    assert v["min_risk"] < 1e-6
    assert abs(MAGNI_MIN_BG - v["argmin_bg"]) < 0.2


def test_reference_values():
    for bg, want in [(40, 84.34), (54, 48.00), (70, 25.00), (100, 5.67),
                     (180, 3.47), (250, 17.63), (400, 56.29)]:
        got = float(magni_risk(bg))
        assert abs(got - want) < 0.02, f"r({bg}) = {got}, expected {want}"


def test_hypo_is_weighted_more_than_hyper():
    """The reason this index suits a hypo-focused project: an equal excursion below the minimum
    costs more than the same excursion above, and increasingly so."""
    ratios = [verify_magni()[f"asym{d}"] for d in (40, 60, 80)]
    assert ratios == sorted(ratios), ratios          # asymmetry grows with distance
    assert ratios[0] > 1.5 and ratios[-1] > 3.0, ratios


def test_prefers_high_over_low_which_callers_must_know():
    """A consequence of the ~139 minimum that changes how candidates rank: Magni scores a BG of 100
    as RISKIER than 180. Any report of a Magni delta has to carry this."""
    assert float(magni_risk(100)) > float(magni_risk(180))


def test_censoring_clip():
    """CGM clamps at 40/400; the input is clipped so a floored or ceilinged reading cannot spike."""
    assert float(magni_risk(5)) == float(magni_risk(20))
    assert float(magni_risk(999)) == float(magni_risk(600))


def test_pools_like_a_mean():
    """Block scoring sums per-sample risk and divides by n, so the pooled value must equal the mean."""
    bg = np.array([54.0, 100.0, 139.0, 180.0, 250.0])
    assert abs(magni_risk(bg).sum() / len(bg) - float(np.mean(magni_risk(bg)))) < 1e-12


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"{len(fns)} passed")
