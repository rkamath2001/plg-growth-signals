"""Run the whole Sangam pipeline: generate synthetic data, analyze it, write charts
and the findings memo, then grade everything against the planted ground truth.

    python run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from sangam import cohorts, readme, report
from sangam.experiment import simulate
from sangam.generate import generate
from sangam.pqa import account_rollup, score
from sangam.tools import (acquisition_channel_ranking, dataset, sales_trigger_threshold,
                          signin_provider_ranking, work_email_prompt_whatif, connector_identity,
                          viral_loops)


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
    results["sales_trigger"] = sales_trigger_threshold()
    results["channel_ranking"] = acquisition_channel_ranking()
    results["provider_ranking"] = signin_provider_ranking()
    results["work_email_whatif"] = work_email_prompt_whatif()
    results["connector_identity"] = connector_identity()
    results["viral_loops"] = viral_loops()
    from sangam.policy import examples
    results["reward_guidelines"] = examples()

    print("4/4 Writing charts and memo ...")
    report.retention_chart(cohorts.curves(ds), out / "retention_by_activation.png")
    report.simpson_chart(results["simpson_check"], ds, out / "desktop_simpson.png")
    report.experiment_chart(results["experiment"], out / "experiment_design.png")
    report.threshold_chart(results["sales_trigger"], out / "sales_trigger_threshold.png")
    report.findings_memo(results, prospects.head(8), out / "findings.md")
    report.loops_chart(results["viral_loops"], out / "viral_loops.png")
    report.write_json(results, out / "results.json")

    print("Grading against planted ground truth and rendering README ...")
    from evals.run_evals import collect
    ev = collect()
    readme.render(results, ev, Path("README.md"))
    for k, v in results.items():
        if "finding" in v:
            print(f"  - {v['finding']}")
    n = sum(r["passed"] for k in ("analytics", "policy", "rubric_self_test") for r in ev[k])
    t = sum(len(ev[k]) for k in ("analytics", "policy", "rubric_self_test"))
    print(f"Done. {n}/{t} eval checks passed. See reports/ and README.md.")


if __name__ == "__main__":
    main()
