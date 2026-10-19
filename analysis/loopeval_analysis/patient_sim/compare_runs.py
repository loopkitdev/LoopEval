"""Two cohort runs side by side on eda's statistics (validate.compare → each run's compare_pilot.csv): the donors' p50,
each run's p50 and two-sample KS p-value per statistic (and sensor family where instrument-dependent), and the count
matched (KS p > 0.05) out of 51. The match targets and their meaning: docs/agents/additive.md → "Match targets".

    python -m loopeval_analysis.patient_sim.compare_runs RUN_A RUN_B
"""
import sys

import pandas as pd


def main(a: str, b: str):
    A = pd.read_csv(a + "/compare_pilot.csv").set_index(["stat", "group"])
    B = pd.read_csv(b + "/compare_pilot.csv").set_index(["stat", "group"])
    D = pd.DataFrame({"real": A.real_p50, a: A.sim_p50, b: B.sim_p50, "ks_" + a: A.ks_p, "ks_" + b: B.ks_p})
    pd.set_option("display.width", 220); pd.set_option("display.max_rows", 80)
    print(D.round(3).to_string())
    print("matched:", int((A.ks_p > 0.05).sum()), int((B.ks_p > 0.05).sum()), "of", len(A))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
