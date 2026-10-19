"""Run the whole Sangam pipeline: generate synthetic data, analyze it, write charts
and the findings memo, then grade everything against the planted ground truth.

    python run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from sangam import cohorts, report
from sangam.experiment import simulate
from sangam.generate import generate
from sangam.pqa import account_rollup, score
from sangam.tools import dataset


def main():
    out = Path("reports")
    out.mkdir(exist_ok=True)
    print("1/4 Generating synthetic data ...")
    generate("data")
    ds = dataset("data")

    print("2/4 Running cohort analyses ...")
    results = {
        "headline_inflation": cohorts.headline_inflation(ds),
        "activation_test": cohorts.activation_test(ds),
        "connector_breadth": cohorts.connector_breadth(ds),
        "simpson_check": cohorts.simpson_check(ds, "desktop"),
        "channel_view": cohorts.channel_view(ds),
    }

    print("3/4 Scoring accounts and simulating outreach experiments ...")
    s = score(account_rollup(ds))
    prospects = s[~s.is_customer]
    # Ground truth is used ONLY to simulate experiment outcomes, never to score.
    truth = pd.read_csv("data/ground_truth/accounts_truth.csv").set_index("account_id").segment
    test = prospects[prospects.min_signal & ~prospects.noise_flag].head(200)
    results["experiment"] = simulate(test, set(truth[truth == "prospect_hot"].index), test.users)
    prospects.to_csv(out / "product_qualified_accounts.csv")

    print("4/4 Writing charts and memo ...")
    report.retention_chart(cohorts.curves(ds), out / "retention_by_activation.png")
    report.simpson_chart(results["simpson_check"], ds, out / "desktop_simpson.png")
    report.experiment_chart(results["experiment"], out / "experiment_design.png")
    report.findings_memo(results, prospects.head(8), out / "findings.md")
    report.write_json(results, out / "results.json")
    for k, v in results.items():
        if "finding" in v:
            print(f"  - {v['finding']}")
    print("Done. See reports/ and run `python -m evals.run_evals` to grade.")


if __name__ == "__main__":
    main()
