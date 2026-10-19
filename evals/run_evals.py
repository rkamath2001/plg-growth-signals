"""Sangam eval harness.

Two layers, both graded against the planted ground truth:

  analytics  Does the deterministic analysis recover what we planted? Runs anywhere,
             no model or credentials needed.
  policy     Do plain-language reward guidelines compile, render and get flagged
             correctly? Uses the reviewed compilations offline; with --agent the
             policy compiler runs live and is graded against them.
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
                          signin_provider_ranking, work_email_prompt_whatif, connector_identity,
                          viral_loops)

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
    check("Teammate invites retain best; invites and LinkedIn lead on pipeline",
          chan["teammate_invite"]["by_retention"] == 1
          and {k for k, v in chan.items() if v["by_pipeline"] <= 2} == {"teammate_invite", "linkedin"},
          f"retention rank {chan['teammate_invite']['by_retention']}; pipeline top 2: "
          f"{sorted(k for k, v in chan.items() if v['by_pipeline'] <= 2)}")
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
    con = connector_identity()
    n, g = con["naive"], con["guarded"]
    check("Naive connector matching produces false positives", n["precision"] < 0.8 and n["phantom_ready"] > 0,
          f"naive precision {n['precision']}, {n['phantom_ready']} phantom sales-ready accounts")
    check("Guarded connector matching is precise and adds real sales-ready accounts",
          g["precision"] >= 0.95 and g["phantom_ready"] == 0 and g["new_correct_ready"] > 0,
          f"precision {g['precision']}, +{g['new_correct_ready']} real ready, {g['phantom_ready']} phantom")
    top_guard = max(con["naive_errors_by_guard"], key=con["naive_errors_by_guard"].get)
    check("Community and side-project workspaces are the main false-positive source",
          top_guard.startswith("community"), f"{con['naive_errors_by_guard']}")

    lp = viral_loops()
    sc = pd.DataFrame(lp["scorecard"]).set_index("loop")
    land = pd.DataFrame(lp["expand_vs_land"]).set_index("loop")
    sim = lp["reward_simulation"]
    check("Shared agents have the highest viral coefficient on activated users",
          sc.k_activated_per_100.idxmax() == "agent", f"{sc.k_activated_per_100.to_dict()}")
    check("Shared spaces retain recipients best", sc.recipient_w8_retention.idxmax() == "space",
          f"{sc.recipient_w8_retention.round(3).to_dict()}")
    check("Shared assets seed the most new companies", land.companies_seeded.idxmax() == "asset",
          f"{land.companies_seeded.to_dict()}")
    check("Embeds and digests convert worst per share",
          set(sc.signup_per_share.nsmallest(2).index) == {"embed", "digest"},
          f"{sc.signup_per_share.round(3).to_dict()}")
    check("Referral sign-ups activate least", sc.activation_of_signups.idxmin() == "referral",
          f"{sc.activation_of_signups.round(3).to_dict()}")
    check("Rewarding shares sent maximizes shares but not activated users",
          max(sim, key=lambda a: sim[a]["shares"]) == "per_share_sent"
          and sim["per_share_sent"]["incremental_activated"] < sim["per_activation_weighted"]["incremental_activated"],
          f"shares {sim['per_share_sent']['shares']:,}; activated {sim['per_share_sent']['incremental_activated']:+} "
          f"vs {sim['per_activation_weighted']['incremental_activated']:+}")
    sa, wt = sim["stage_aware"], sim["per_activation_weighted"]
    check("Stage-aware rewards keep the pipeline gains at a fraction of the cost",
          sa["extra_prospects_over_trigger"] >= 0.9 * wt["extra_prospects_over_trigger"]
          and sa["rewards_paid"] <= 0.2 * wt["rewards_paid"],
          f"{sa['extra_prospects_over_trigger']} vs {wt['extra_prospects_over_trigger']} prospects over trigger; "
          f"{sa['rewards_paid']:,} vs {wt['rewards_paid']:,} rewards paid")
    return out


# ---------- reward guidelines layer ----------

EXAMPLES = Path(__file__).resolve().parent.parent / "policies" / "examples"
PLUMBING = re.compile(r"reward_event|pre_contract|post_contract|same_company|other_company|recipient_|"
                      r"\bTrue\b|\bFalse\b|\bnull\b|[{}]|yaml|json", re.I)


def policy_checks(live: bool = False) -> list[dict]:
    from sangam.policy import NotReady, Policy, approve, lint, render_card, simulate
    from sangam.policy_compiler import compile_live, grade_compile
    from sangam.tools import _outcomes, _ready_accounts
    out = []

    def check(name, ok, detail):
        out.append({"check": name, "passed": bool(ok), "detail": detail})

    docs = {p.stem.replace(".reviewed", ""): Policy.model_validate_json(p.read_text())
            for p in sorted(EXAMPLES.glob("*.reviewed.json"))}
    good, sloppy, amb = docs["growth_team_q4"], docs["launch_blitz"], docs["partner_draft"]
    ds, rule, oc = dataset(), _ready_accounts()[1], _outcomes()

    warn = [i for i in lint(good) if i["severity"] == "warning"]
    sim = simulate(good, ds, rule, oc)["policy"]
    check("Sound guidelines: no warnings, and activation gains at a low reward cost",
          not warn and sim["incremental_activated"] > 0 and sim["rewards_per_incremental_activated"] <= 10,
          f"{len(warn)} warnings; +{sim['incremental_activated']} activated users at "
          f"{sim['rewards_per_incremental_activated']} rewards each")
    ids = {i["id"] for i in lint(sloppy)}
    need = {"pays_on_share", "pays_licensed", "personal_email", "no_cap", "external_no_admin"}
    check("Sloppy guidelines: every planted problem is flagged in plain language",
          need <= ids, f"flagged {len(ids & need)}/{len(need)}; missing {sorted(need - ids) or 'none'}")
    blocked = 0
    for fn in (lambda: simulate(amb, ds, rule, oc), lambda: approve(amb, "/tmp/_never_written.md")):
        try:
            fn()
        except NotReady:
            blocked += 1
    check("Ambiguous guidelines: questions raised, simulation and approval blocked",
          len(amb.open_questions) >= 2 and blocked == 2,
          f"{len(amb.open_questions)} open questions; blocked {blocked}/2")
    texts = [render_card(p) for p in docs.values()] + [i["text"] for p in docs.values() for i in lint(p)]
    leaks = sorted({m.group(0) for t in texts for m in PLUMBING.finditer(t)})
    check("Cards and warnings contain no field names or code", not leaks, f"leaks: {leaks or 'none'}")
    card = render_card(good).lower()
    say = ["first agent action", "already have a license", "admin", "10 rewards per person", "customers"]
    check("Card states what the guidelines said", all(s in card for s in say),
          f"{sum(s in card for s in say)}/{len(say)} required statements")
    mutations = [("pays on shares", {"reward_event": "share_sent"}),
                 ("pays licensed colleagues", {"pay_for_licensed_recipients": True}),
                 ("guessed instead of asking", {"open_questions": []}),
                 ("widened who counts", {"pre_contract": ["same_company", "other_company"]})]
    caught = sum(bool(grade_compile(p.model_copy(update=m), p)) for _, m in mutations for p in docs.values()
                 if p.model_copy(update=m) != p)
    possible = sum(1 for _, m in mutations for p in docs.values() if p.model_copy(update=m) != p)
    exact = all(not grade_compile(p, p) for p in docs.values())
    check("Compile grader passes reviewed compilations and catches planted mistakes",
          exact and caught == possible, f"self-match {exact}; caught {caught}/{possible}")
    if live:
        for name, want in docs.items():
            got = compile_live((EXAMPLES / f"{name}.md").read_text())
            diffs = grade_compile(got, want)
            check(f"Live compile matches reviewed policy: {name}", not diffs, "; ".join(diffs) or "match")
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


def collect(agent: bool = False) -> dict:
    results = {"analytics": analytics_checks(), "policy": policy_checks(live=agent)}
    facts = fact_sheet()
    results["rubric_self_test"] = rubric_self_test(facts)
    if agent:
        from sangam.agent import ask
        graded = []
        for item in GOLDEN:
            ans = ask(item["question"])
            g = grade(ans, item, facts)
            g["answer"] = ans
            graded.append(g)
        results["agent"] = graded
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", action="store_true", help="also grade the live Bedrock agent")
    ap.add_argument("--out", default="reports/eval_results.json")
    args = ap.parse_args()

    results = collect(args.agent)

    print("\nSangam evals\n" + "=" * 60)
    total = passed = 0
    for layer in ("analytics", "policy", "rubric_self_test"):
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
