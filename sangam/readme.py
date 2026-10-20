"""Render README.md from the pipeline's results, so the prose never drifts from the data."""

from __future__ import annotations

from pathlib import Path

from .loops import LOOP_LABEL


def _pct(x: float) -> str:
    return f"{x:.0%}"


def _channel_table(chan: dict) -> str:
    rows = ["| Channel | Sign-ups | Activation | Week-8 retention | Resolved to a company | "
            "Sales-ready accounts per 1,000 | Rank: volume / retention / pipeline |",
            "|---|---|---|---|---|---|---|"]
    for x in chan["table"]:
        rows.append(f"| {x['source']} | {x['signups']:,} | {_pct(x['activation_rate'])} | {_pct(x['w8_retention'])} | "
                    f"{_pct(x['company_resolved'])} | {x['ready_per_1k']} | "
                    f"{x['by_volume']} / {x['by_retention']} / {x['by_pipeline']} |")
    return "\n".join(rows)


def _provider_table(prov: dict) -> str:
    rows = ["| Provider | Sign-ups | Activation | Week-8 retention | Resolved to a company | Private relay | "
            "Users at sales-ready accounts per 1,000 | Rank: volume / retention / visibility / pipeline |",
            "|---|---|---|---|---|---|---|---|"]
    for x in prov["table"]:
        rows.append(f"| {x['provider']} | {x['signups']:,} | {_pct(x['activation_rate'])} | {_pct(x['w8_retention'])} | "
                    f"{_pct(x['company_resolved'])} | {_pct(x['private_relay'])} | {x['ready_users_per_1k']} | "
                    f"{x['by_volume']} / {x['by_retention']} / {x['by_visibility']} / {x['by_pipeline']} |")
    return "\n".join(rows)


def _connector_table(con: dict) -> str:
    e, n, g = con["email_only"], con["naive"], con["guarded"]
    return "\n".join([
        "| Matcher | Users attributed | Precision | Hidden employees recovered | Sales-ready accounts (correct / phantom) |",
        "|---|---|---|---|---|",
        f"| Work email only | - | - | - | {e['correct_ready']} / {e['phantom_ready']} |",
        f"| Naive connector match | {n['users_attributed']} | {_pct(n['precision'])} | {_pct(n['recall_of_hidden'])} | "
        f"{n['correct_ready']} / {n['phantom_ready']} |",
        f"| Guarded connector match | {g['users_attributed']} | {_pct(g['precision'])} | {_pct(g['recall_of_hidden'])} | "
        f"{g['correct_ready']} / {g['phantom_ready']} |"])


def _loop_table(lp: dict) -> str:
    land = {r["loop"]: r for r in lp["expand_vs_land"]}
    rows = ["| Loop | Shares | Sign-up per share | Sign-ups that activate | Activated recipients per 100 users | "
            "Median days to sign-up | Recipient week-8 retention | Companies seeded | Prospects pushed over trigger |",
            "|---|---|---|---|---|---|---|---|---|"]
    for x in lp["scorecard"]:
        l = land[x["loop"]]
        rows.append(f"| {LOOP_LABEL[x['loop']]} | {x['shares']:,} | {x['signup_per_share']:.1%} | "
                    f"{_pct(x['activation_of_signups'])} | {x['k_activated_per_100']} | {x['median_cycle_days']:g} | "
                    f"{_pct(x['recipient_w8_retention'])} | {l['companies_seeded']} | {l['prospects_pushed_over_trigger']} |")
    return "\n".join(rows)


ARM_LABEL = {"no_reward": "No reward (status quo)", "per_share_sent": "Per share sent",
             "per_signup": "Per recipient sign-up", "per_activation": "Per recipient first agent action",
             "per_activation_weighted": "Per first agent action, weighted by share type",
             "stage_aware": "Stage-aware, sharer rewarded (see below)",
             "stage_aware_recipient": "Stage-aware, recipient rewarded",
             "stage_aware_both": "Stage-aware, sharer and recipient rewarded"}


def _reward_table(lp: dict) -> str:
    rows = ["| Reward fires... | Shares | Extra activated users | North-star lift (weekly agent-active users) | "
            "Rewards paid | Rewards per extra activated user | Extra prospects over trigger | "
            "Extra companies seeded by customers |",
            "|---|---|---|---|---|---|---|---|"]
    for arm, r in lp["reward_simulation"].items():
        per = r["rewards_per_incremental_activated"]
        rows.append(f"| {ARM_LABEL[arm]} | {r['shares']:,} | {r['incremental_activated']:+,} | {r.get('north_star_lift', 0):+,} | "
                    f"{r['rewards_paid']:,} | "
                    f"{per if per is not None else '-'} | {r['extra_prospects_over_trigger']} | "
                    f"{r['extra_companies_seeded_by_customers']} |")
    return "\n".join(rows)


def _evals_block(ev: dict) -> str:
    lines, total, passed = [], 0, 0
    for layer in ("analytics", "policy", "rubric_self_test"):
        lines.append(f"[{layer}]")
        for r in ev[layer]:
            total += 1
            passed += r["passed"]
            lines.append(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['check']}")
    lines.append(f"{passed}/{total} checks passed")
    return "\n".join(lines), passed, total


def _guidelines(g: dict) -> str:
    rows = ["| Guidelines (prose) | What the policy owner sees |", "|---|---|"]
    for k, x in g.items():
        warns = [i for i in x["issues"] if i["severity"] == "warning"]
        if x["open_questions"]:
            seen = f"{len(x['open_questions'])} questions to answer; simulation and approval blocked until they are"
        elif warns:
            sim = x["simulation"]["policy"]
            seen = (f"{len(warns)} warnings; {sim['rewards_paid']:,} rewards for {sim['incremental_activated']:+,} "
                    f"activated users ({sim['rewards_per_incremental_activated']} each)")
        else:
            sim = x["simulation"]["policy"]
            seen = (f"No warnings; {sim['rewards_paid']:,} rewards for {sim['incremental_activated']:+,} activated "
                    f"users ({sim['rewards_per_incremental_activated']} each); ready to approve")
        rows.append(f"| [{x['title']}]({x['path']}) | {seen} |")
    return "\n".join(rows)


def render(r: dict, ev: dict, path: Path) -> None:
    inf, act, conn, sim, exp = (r["headline_inflation"], r["activation_test"], r["connector_breadth"],
                                r["simpson_check"], r["experiment"])
    trig, chan, prov, wif, con, lp = (r["sales_trigger"], r["channel_ranking"], r["provider_ranking"],
                                      r["work_email_whatif"], r["connector_identity"], r["viral_loops"])
    c = {row["connectors_w0"]: row["w8_retention"] for row in conn["table"]}
    rule, naive, tiers = trig["recommended_rule"], trig["signup_count_rule"], trig["tiers"]
    a_ret, q_ret = act["cohorts"]["agent_action"]["w8_retention"], act["cohorts"]["question_only"]["w8_retention"]
    sa, wt, sent = (lp["reward_simulation"]["stage_aware"], lp["reward_simulation"]["per_activation_weighted"],
                    lp["reward_simulation"]["per_share_sent"])
    sc = {x["loop"]: x for x in lp["scorecard"]}
    g = r["reward_guidelines"]
    blitz, draft, q4 = g["launch_blitz"], g["partner_draft"], g["growth_team_q4"]
    blitz_warn = "\n".join(f"> - {i['text']}" for i in blitz["issues"] if i["severity"] == "warning")
    draft_q = "\n".join(f"> {n}. {q}" for n, q in enumerate(draft["open_questions"], 1))
    q4_card = q4["card"].replace("## ", "#### ", 1)
    evals_text, passed, total = _evals_block(ev)
    n_contracts = int(round(rule["contracts_captured"] / rule["recall"])) if rule["recall"] else 0

    md = f"""# Sangam: growth signals for an AI workspace product

**Sangam** (Sanskrit: *confluence*) is where independent streams meet and become one river. In product-led growth, the streams are individual adopters who sign up on their own, the colleagues they share with, and the enterprise rollouts that follow. This project finds where they converge.

> **All data is synthetic.** The product modeled is a generic AI workspace (an assistant that answers questions, takes agent actions, shares agents and outputs, and connects to apps), described from public information only. Company names and `.example` domains are invented. Nothing here reflects any company's internal data.

## In 60 seconds

- **Activation is the first agent action.** Users who complete one in their first week retain at {_pct(a_ret)} at week 8, versus {_pct(q_ret)} for those who only ask questions.
- **Start an enterprise sales motion at {rule['min_activated']}+ activated independent users at a company**, not at a sign-up count: those companies convert at {_pct(rule['precision'])} versus a {_pct(trig['baseline_conversion'])} baseline. At {rule['min_activated'] - 1} users, run champion enablement instead.
- **Shared agents are the strongest viral loop; shared assets are the landing loop** that seeds new companies. Embeds and digests barely convert.
- **Pay sharing rewards when the recipient completes a first agent action, and tie them to the account's stage**: same-company shares before a contract, external shares after it. In simulation that keeps the same pipeline gains as uniform rewards while paying {sa['rewards_paid']:,} rewards instead of {wt['rewards_paid']:,}.
- **Reward policy is written in plain language.** Teams submit prose guidelines and approve a plain-English card; the framework flags pay-per-share and uncapped schemes, and asks rather than guesses when wording is ambiguous.
- **Visibility is the hidden constraint.** Apple and Amazon sign-ins almost never reveal a company. Connected Slack, Teams and Jira workspaces help, but only with guards: naive matching is {_pct(con['naive']['precision'])} accurate and invents sales-ready accounts from school clubs and side projects.
- **Everything is graded**: {passed} of {total} checks pass against the expected results, including tests of the grader itself.

## Quick start

```bash
pip install -r requirements.txt
python run.py                 # generate data, analyze, grade, write reports/ and this README
python -m evals.run_evals     # grade the analysis against the expected results
```

The agent is optional and needs AWS credentials with Amazon Bedrock model access:

```bash
export AWS_REGION=us-west-2            # optional: SANGAM_MODEL_ID=<bedrock model id>
export AWS_BEARER_TOKEN_BEDROCK=<key>  # or a Bedrock API key instead of an AWS CLI profile
python -m sangam.agent "Which accounts should business development contact this week, and why?"
python -m evals.run_evals --agent      # grade the agent's answers to the golden questions
```

## Findings

Each finding is checked against the expected result. The [findings memo](reports/findings.md) has the detail.

### 1. Activation is the first agent action, not the first question

External users who complete an agent action in their first week retain at {_pct(a_ret)} at week 8, versus {_pct(q_ret)} for question-only users, and the gap holds in every segment. It's observational: high-intent users both act and stay, so the next step is an onboarding experiment that nudges a first agent action.

![Retention by week-0 behavior](reports/retention_by_activation.png)

### 2. Customer zero flatters every headline

A large internal deployment with mandated use lifts week-8 retention from {_pct(inf['w8_retention_external_only'])} to {_pct(inf['w8_retention_all_users'])}. External users are always reported separately.

### 3. Breadth predicts retention

Users who link three or more connectors in their first week retain at {_pct(c['3+'])}, versus {_pct(c['1-2'])} for one or two.

### 4. Not every lift is real

Desktop-app users retain {sim['aggregate_lift']:+.0%} better in aggregate and about {sim['weighted_within_lift']:+.0%} inside every segment. The internal rollout installed the app by default, so the aggregate is a mix effect (Simpson's paradox), and the analysis flags it automatically.

![Desktop app lift disappears within segments](reports/desktop_simpson.png)

### 5. Test sales plays at the account level

Colleagues share the outcome of outreach. Splitting users inside a company leaks treatment into the control group: in simulation it reports {exp['user_level_estimate']['mean']:+.1%} against a true lift of {exp['true_effect']:+.1%}, while randomizing whole accounts recovers {exp['account_level_estimate']['mean']:+.1%}.

![Experiment design comparison](reports/experiment_design.png)

### 6. Start the sales motion at {rule['min_activated']} activated adopters

Learned from {n_contracts} observed contracts. Companies with {rule['min_activated']}+ independent users who completed an agent action convert at {_pct(rule['precision'])} versus a {_pct(trig['baseline_conversion'])} baseline ({trig['lift_over_baseline']}x). At exactly {rule['min_activated'] - 1} they convert at {_pct(tiers['warm_champion']['conversion'])}, a champion-enablement tier; below that, at {_pct(tiers['self_serve']['conversion'])}. The best rule built on raw sign-up counts scores F1 {naive['f1']:.2f} against {rule['f1']:.2f}, because event spikes inflate sign-ups without activating.

![Sales trigger threshold](reports/sales_trigger_threshold.png)

{len(trig['tied_rules'])} candidate rules are statistically tied ({', '.join(trig['tied_rules'])}), so the method bootstraps F1, treats everything within one standard error of the best as a tie, and picks the simplest. A plain "highest F1" search once chose "1+ users across 4+ functions": technically equivalent to 4 users across 4 functions, but nonsense to a seller.

### 7. Rank acquisition channels by pipeline, not volume

{chan['finding']}

{_channel_table(chan)}

**Attribution warning.** {chan['attribution_note']}

### 8. Sign-in provider decides who you can see

{prov['finding']}

{_provider_table(prov)}

{wif['finding']} *({wif['method']})*

### 9. Connected workspaces reveal employers, with guards against false positives

People connect their employer's Slack, Teams or Jira, but also their kid's robotics team Slack, hobby groups, big open communities, and clients' workspaces as contractors, and some of those share a company's name.

{_connector_table(con)}

{con['finding']}

The guarded matcher trusts verified domains; treats a matching name as a clue that needs a colleague resolved by work email to corroborate it; drops guest memberships; drops workspaces whose connected users already resolve to 3+ companies, the signature of a school club; skips users whose evidence points to two companies; and never overrides a work email. {con['caveat']}

### 10. Viral loops: agent shares grow, asset shares land, rewards must fire on activation

{lp['finding']}

![Viral loops](reports/viral_loops.png)

{_loop_table(lp)}

**Reward policy simulation.** Eight ways to reward sharing, on the same population:

{_reward_table(lp)}

The **stage-aware** policy pays on the recipient's first agent action, weights agent and space shares higher, rewards *same-company* shares before a company has a contract (each activated colleague moves it toward the sales trigger), rewards *external* shares to customers and partners after a contract (customers become a distribution channel), and never pays for colleagues who are already licensed. Paying per share sent nearly doubles shares ({sent['shares']:,}) for the smallest gain in activated users.

{lp['caveat']}

### 11. Reward guidelines in plain language

The people who set reward policy (growth, finance, partner teams) write guidelines as ordinary prose and approve a plain-English policy card. They never see a schema. A policy agent compiles the prose; the framework renders it back as a card, flags problems in plain language, and simulates the outcome against the status quo. The compiler never guesses: anything ambiguous becomes a question for the owner, and a policy with open questions can't be simulated or approved.

{_guidelines(g)}

The launch-blitz memo ("$10 for every link they share, to anyone ... no limits") comes back with:

{blitz_warn}

The partner draft ("reward users when their teammates start using the product in a meaningful way") comes back with questions instead of guesses:

{draft_q}

<details><summary>The full policy card for the Q4 guidelines</summary>

{q4_card}

{q4['outcome']}

</details>

```bash
python -m sangam.policy policies/examples/growth_team_q4.md            # card, warnings, expected outcome
python -m sangam.policy policies/examples/growth_team_q4.md --approve  # record approval of the card
```

New guidelines compile live with AWS credentials; the examples also ship with reviewed compilations, so the evals grade the live compiler against them. How people respond to incentives is kept apart from policy: it is the growth team's stated assumption, tested by A/B test, not something a policy author sets.

## How it works

```
sangam/
  generate.py    synthetic users, accounts, events, shares, workspaces; configurable effects and noise
  identity.py    resolve self-serve users to companies by email domain
  dhruva.py      the governed metric layer: one definition of "active", "retained", "activated"
  cohorts.py     retention, activation, breadth, Simpson's-paradox check
  pqa.py         product-qualified account scoring, reasons, plays, noise suppression
  motions.py     sales trigger, channel and sign-in provider rankings, work-email what-if
  connectors.py  naive vs guarded identity from connected Slack, Teams and Jira workspaces
  loops.py       viral loop scorecard, expand vs land
  policy.py      reward policy: plain-English card, warnings, simulation, approval
  policy_compiler.py  agent that compiles prose guidelines; asks instead of guessing
  experiment.py  outreach holdout simulation: account vs user randomization
  tools.py       the functions the agent may call (testable without a model)
  agent.py       Strands agent on Amazon Bedrock
  report.py      charts and findings memo;  readme.py renders this README from the results
evals/
  golden.json    golden questions with required facts, caveats and forbidden claims
  run_evals.py   grades the analysis, the reward-guidelines pipeline, the rubric itself,
                 and (optionally) the live agent and policy compiler
policies/examples/  sample guidelines: sound, sloppy and ambiguous
```

**Dhruva, the north star and metric layer.** Named for the pole star you navigate by. The north star is weekly agent-active users, external users only (peak {r['north_star']['peak_weekly_agent_active_users']:,}). Each activated user is agent-active in {r['north_star']['agent_active_rate_activated']:.0%} of weeks, versus {r['north_star']['agent_active_rate_question_only']:.0%} for a question-only user, so every reward program is judged by its north-star lift and its cost. Every number, in a chart or in an agent's answer, comes from one set of definitions.

**An agent you can check.** The agent can only call governed tools. Its instructions require sample sizes, external-only reporting, a within-segment check before crediting any feature, a named alternative explanation, and a confirming experiment. The eval rubric scores each answer on required facts, required caveats and forbidden claims, and the rubric is itself tested: a known-good answer must pass and a known-bad one must fail. That self-test once caught the grader reading "5 activated users" as "5%" and failing a correct answer.

## Eval results

```
{evals_text}
```

## Limits

- Synthetic effects are cleaner than real ones; real data is noisier. Thresholds are starting points to tune against real outcomes.
- The sales trigger is fit on {n_contracts} contracts, so several rules tie; refit it as contracts accumulate and by segment.
- Activation and channel findings are observational. Only experiments settle cause.
- The reward simulation rests on stated behavioral assumptions (`BEHAVIOR` in `sangam/policy.py`); its value is the measurement design. Viral coefficients are single-generation.
- Using a personal sign-up's activity or workspace metadata to prompt outreach must respect the permissions users granted and regional law. Individuals get in-product nudges, not sales calls.

## License

MIT. Built by Rahul Kamath.
"""
    path.write_text(md, encoding="utf-8")
