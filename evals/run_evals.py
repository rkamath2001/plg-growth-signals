"""Sangam eval harness.

Two layers, both graded against the planted ground truth:

  analytics  Does the deterministic analysis recover what we planted? Runs anywhere,
             no model or credentials needed.
  agent      Does the agent's answer to each golden question state the right facts,
             carry the required caveats and avoid forbidden claims? Needs Bedrock.

The rubric itself is tested too: a known-good and a known-bad answer must score
as expected, so a lenient grader can't pass a sloppy agent.

Usage:
  python -m evals.run_evals            # analytics layer + rubric self-test
  python -m evals.run_evals --agent    # also grade the live agent
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

from sangam import cohorts
from sangam.experiment import simulate
from sangam.pqa import account_rollup, score
from sangam.tools import (acquisition_channel_ranking, dataset, sales_trigger_threshold,
                          signin_provider_ranking, work_email_prompt_whatif)

ROOT = Path(__file__).resolve().parent
GOLDEN = json.loads((ROOT / "golden.json").read_text())


# ---------- analytics layer ----------

def analytics_checks(data_dir: str = "data") -> list[dict]:
    ds = dataset(data_dir)
    truth = pd.read_csv(Path(data_dir) / "ground_truth" / "accounts_truth.csv").set_index("account_id").segment
    out = []

    def check(name, passed, detail):
        out.append({"check": name, "passed": bool(passed), "detail": detail})

    inf = cohorts.headline_inflation(ds)
    check("Customer zero inflation detected", inf["inflation_points"] >= 3,
          f"{inf['inflation_points']} points of W8 retention from internal users")

    act = cohorts.activation_test(ds)
    check("Agent action beats question-only for activation",
          act["ci95"][0] > 0.1 and all(v > 0.1 for v in act["lift_within_segment"].values()),
          f"lift {act['lift_agent_vs_question']:+.3f}, CI {act['ci95']}, within {act['lift_within_segment']}")

    conn = {r["connectors_w0"]: r["w8_retention"] for r in cohorts.connector_breadth(ds)["table"]}
    check("3+ connectors retain better than 0-2", conn["3+"] > conn["1-2"] + 0.1, str(conn))

    sim = cohorts.simpson_check(ds, "desktop")
    check("Desktop app flagged as confounded (Simpson's trap)", sim["confounded"],
          f"aggregate {sim['aggregate_lift']:+.3f} vs within {sim['weighted_within_lift']:+.3f}")

    s = score(account_rollup(ds))
    p = s[~s.is_customer].copy()
    p["truth"] = truth.reindex(p.index)
    top = p.head(30)
    prec = (top.truth == "prospect_hot").mean()
    check("PQA precision@30 >= 0.8", prec >= 0.8, f"precision@30 = {prec:.2f}")
    check("No webinar-noise account in the top 30", (top.truth == "prospect_webinar").sum() == 0,
          f"{(top.truth == 'prospect_webinar').sum()} noise accounts in top 30")
    web = p[p.truth == "prospect_webinar"]
    false_flags = int(p[(p.truth != "prospect_webinar") & p.noise_flag].shape[0])
    check("All webinar spikes flagged, no false flags", web.noise_flag.all() and false_flags == 0,
          f"{int(web.noise_flag.sum())}/{len(web)} flagged, {false_flags} false flags")

    test = p[p.min_signal & ~p.noise_flag].head(200)
    exp = simulate(test, set(truth[truth == "prospect_hot"].index), test.users)
    a, u = exp["account_level_estimate"]["mean"], exp["user_level_estimate"]["mean"]
    check("Account-level design recovers true lift (within 1.5 pts)", abs(a - exp["true_effect"]) <= 0.015,
          f"estimate {a:+.3f} vs true {exp['true_effect']:+.3f}")
    check("User-level design underestimates (interference)", u < 0.6 * exp["true_effect"],
          f"user-level {u:+.3f} vs true {exp['true_effect']:+.3f}")
    trig = sales_trigger_threshold()
    rule, naive = trig["recommended_rule"], trig["signup_count_rule"]
    check("Sales trigger recovers the planted tipping point (5 activated users)",
          4 <= rule["min_activated"] <= 6,
          f"learned {rule['min_activated']}+ activated users across {rule['min_functions']}+ functions")
    check("Activated-user trigger beats a sign-up-count trigger", rule["f1"] >= naive["f1"] + 0.1,
          f"F1 {rule['f1']} vs {naive['f1']}")

    chan = {r["source"]: r for r in acquisition_channel_ranking()["table"]}
    check("Teammate invites rank first on pipeline and retention",
          chan["teammate_invite"]["by_pipeline"] == 1 and chan["teammate_invite"]["by_retention"] == 1,
          f"pipeline rank {chan['teammate_invite']['by_pipeline']}, retention rank {chan['teammate_invite']['by_retention']}")
    check("Low-intent social channels rank in the bottom half on retention",
          all(chan[c]["by_retention"] > len(chan) / 2 for c in ("x", "reddit")),
          f"x {chan['x']['by_retention']}, reddit {chan['reddit']['by_retention']} of {len(chan)}")
    prov = {r["provider"]: r for r in signin_provider_ranking()["table"]}
    top2 = {k for k, v in prov.items() if v["by_visibility"] <= 2}
    bottom2 = {k for k, v in prov.items() if v["by_visibility"] >= len(prov) - 1}
    check("Google and email are the most visible providers; Apple and Amazon the least",
          top2 == {"google", "email"} and bottom2 == {"apple", "amazon"},
          f"top {sorted(top2)}, bottom {sorted(bottom2)}")
    wif = work_email_prompt_whatif()
    check("Making hidden adopters visible adds sales-ready accounts",
          wif["ready_accounts_if_all_visible"] > wif["ready_accounts_visible_today"]
          and wif["extra_ready_accounts_at_uptake"] > 0,
          f"{wif['ready_accounts_visible_today']} -> {wif['ready_accounts_if_all_visible']} with full visibility; "
          f"+{wif['extra_ready_accounts_at_uptake']} at {wif['uptake_assumed']:.0%} uptake")
    return out


# ---------- rubric for agent answers ----------

def _numbers(text: str) -> list[float]:
    vals = []
    for m in re.finditer(r"(-?\d+(?:\.\d+)?)\s*(%|pts|points|pp)?", text):
        v = float(m.group(1))
        if m.group(2) == "%":
            vals.append(v / 100)
            continue
        vals.append(v)            # a count, e.g. "5 activated users"
        if v > 1:
            vals.append(v / 100)  # a percentage written without the sign
    return vals


def grade(answer: str, item: dict, facts: dict) -> dict:
    """Score an answer 0-1 on required facts, required caveats and forbidden claims."""
    text = answer.lower()
    nums = _numbers(answer)
    results = []
    for f in item.get("facts", []):
        target = facts[f["key"]]
        ok = any(abs(n - target) <= f.get("tol", 0.03) for n in nums)
        results.append({"type": "fact", "what": f["key"], "target": target, "passed": ok})
    for c in item.get("must_mention", []):
        ok = any(alt in text for alt in c["any_of"])
        results.append({"type": "caveat", "what": c["why"], "passed": ok})
    for c in item.get("must_not_claim", []):
        ok = not re.search(c["pattern"], text)
        results.append({"type": "forbidden", "what": c["why"], "passed": ok})
    s = sum(r["passed"] for r in results) / max(len(results), 1)
    return {"id": item["id"], "score": round(s, 2), "passed": s >= item.get("pass_mark", 0.8), "checks": results}


def fact_sheet() -> dict:
    ds = dataset()
    act = cohorts.activation_test(ds)
    inf = cohorts.headline_inflation(ds)
    sim = cohorts.simpson_check(ds, "desktop")
    return {
        "act_agent": act["cohorts"]["agent_action"]["w8_retention"],
        "act_question": act["cohorts"]["question_only"]["w8_retention"],
        "ret_external": inf["w8_retention_external_only"],
        "ret_all": inf["w8_retention_all_users"],
        "desktop_agg": sim["aggregate_lift"],
        "trigger_k": sales_trigger_threshold()["recommended_rule"]["min_activated"],
    }


def rubric_self_test(facts: dict) -> list[dict]:
    out = []
    for item in GOLDEN:
        fmt = {k: (f"{v:.0%}" if isinstance(v, float) else v) for k, v in facts.items()}
        good = item.get("reference_good", "").format(**fmt)
        bad = item.get("reference_bad", "")
        if not good or not bad:
            continue
        g, b = grade(good, item, facts), grade(bad, item, facts)
        out.append({"check": f"Rubric separates good from bad answer: {item['id']}",
                    "passed": g["passed"] and not b["passed"],
                    "detail": f"good={g['score']}, bad={b['score']}"})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", action="store_true", help="also grade the live Bedrock agent")
    ap.add_argument("--out", default="reports/eval_results.json")
    args = ap.parse_args()

    results = {"analytics": analytics_checks()}
    facts = fact_sheet()
    results["rubric_self_test"] = rubric_self_test(facts)

    if args.agent:
        from sangam.agent import ask
        graded = []
        for item in GOLDEN:
            ans = ask(item["question"])
            g = grade(ans, item, facts)
            g["answer"] = ans
            graded.append(g)
        results["agent"] = graded

    print("\nSangam evals\n" + "=" * 60)
    total = passed = 0
    for layer in ("analytics", "rubric_self_test"):
        print(f"\n[{layer}]")
        for r in results[layer]:
            total += 1
            passed += r["passed"]
            print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['check']}  ({r['detail']})")
    if "agent" in results:
        print("\n[agent]")
        for r in results["agent"]:
            total += 1
            passed += r["passed"]
            print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['id']}  score={r['score']}")
    print(f"\n{passed}/{total} checks passed")
    Path(args.out).parent.mkdir(exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2, default=str))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
