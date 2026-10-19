# Sangam: growth signals for an AI workspace product

**Sangam** (Sanskrit: *confluence*) is where independent streams meet and become one river. In product-led growth, the streams are individual adopters who sign up on their own and the enterprise rollouts that follow. This project finds where they converge.

It is an agentic growth-analytics prototype that:

- ties self-serve sign-ups to companies, and says honestly when it can't,
- runs cohort and retention analysis that handles the classic traps,
- ranks **acquisition channels** by volume, retention and pipeline, which give different answers,
- learns **how many independent freemium adopters a company needs** before an enterprise sales motion pays off,
- scores **product-qualified accounts** with plain-language reasons and a recommended sales or champion play,
- simulates how to test sales outreach so it can prove its own lift,
- lets a **Strands agent on Amazon Bedrock** answer growth questions only through governed metrics,
- and grades all of it against planted ground truth with an **eval harness**.

> **All data is synthetic.** The product modeled is a generic AI workspace (an assistant that answers questions, takes agent actions and connects to apps), described from public information only. Company names and `.example` domains are invented. Nothing here reflects any company's internal data.

## Quick start

```bash
pip install -r requirements.txt
python run.py                 # generate data, analyze, write reports/ (about 5 seconds)
python -m evals.run_evals     # grade the analysis against the planted ground truth
```

The agent is optional and needs AWS credentials with Amazon Bedrock model access:

```bash
export AWS_REGION=us-west-2            # optional: SANGAM_MODEL_ID=<bedrock model id>
python -m sangam.agent "Which accounts should business development contact this week, and why?"
python -m evals.run_evals --agent      # grade the agent's answers to the golden questions
```

## What it finds

Seven findings, each verified against a known planted answer ([full memo](reports/findings.md)).

**1. Activation is the first agent action, not the first question.** External users who complete an agent action in week 0 retain at about three times the rate of question-only users at week 8. The gap holds in every segment. It is observational, so the recommended next step is an onboarding experiment.

![Retention by week-0 behavior](reports/retention_by_activation.png)

**2. Customer zero flatters every headline.** A large internal deployment with mandated use lifts week-8 retention from 27% to 33%. External users are always reported separately.

**3. Breadth predicts retention.** Users who link three or more connectors in week 0 retain far better than those who link one or two.

**4. Not every lift is real.** Desktop-app users retain 20 points better in aggregate, and about 0 points better inside every segment. The internal rollout installed the app by default, so the aggregate is a mix effect (Simpson's paradox). The analysis flags it automatically.

![Desktop app lift disappears within segments](reports/desktop_simpson.png)

**5. Test sales plays at the account level.** In a collaboration product, colleagues share the outcome of outreach. Splitting users inside a company leaks treatment into the control group and understates the lift; randomizing whole accounts recovers it.

![Experiment design comparison](reports/experiment_design.png)

**6. Start the enterprise sales motion at 5 activated adopters, not at a sign-up count.** Learned from observed contract outcomes: companies with 5+ independent users who completed an agent action, across 2+ functions, convert at 70% versus a 5% baseline (14x), and that rule captures 56% of contracts while flagging only 33 accounts. The best rule built on raw sign-up counts does markedly worse (F1 0.47 vs 0.62) because event spikes inflate sign-ups without activating.

![Sales trigger threshold](reports/sales_trigger_threshold.png)

**7. Rank channels by pipeline, not volume.** Search brings the most sign-ups; teammate invites rank 7th on volume but 1st on both retention and sales-ready accounts per 1,000 sign-ups. LinkedIn is the strongest broad channel because work identities resolve to companies. X and Reddit bring volume that rarely retains or resolves.

| Channel | Sign-ups | Activation | Week-8 retention | Resolved to a company | Sales-ready accounts per 1,000 | Rank: volume / retention / pipeline |
|---|---|---|---|---|---|---|
| teammate_invite | 1,147 | 54% | 28% | 67% | 9.6 | 7 / 1 / 1 |
| linkedin | 1,395 | 44% | 19% | 61% | 5.0 | 2 / 3 / 2 |
| search | 1,971 | 42% | 20% | 38% | 3.6 | 1 / 2 / 3 |
| reddit | 1,285 | 32% | 14% | 16% | 3.1 | 4 / 6 / 4 |
| direct | 1,160 | 40% | 19% | 38% | 2.6 | 6 / 3 / 5 |
| youtube | 1,238 | 41% | 16% | 27% | 0.8 | 5 / 5 / 6 |
| webinar | 272 | 14% | 1% | 90% | 0.0 | 8 / 8 / 7 |
| x | 1,295 | 33% | 14% | 20% | 0.0 | 3 / 7 / 7 |

Pipeline ranks below the top three rest on fewer than 5 accounts each, so treat their order as noise. Accounts are credited to the channel of their first sign-up (first-touch); that choice is stated so it can be challenged, and channel budget shifts should be confirmed with geo or time holdouts.

## How it works

```
sangam/
  generate.py    synthetic users, accounts, events, with planted effects and noise
  identity.py    resolve self-serve users to companies by email domain
  dhruva.py      the governed metric layer: one definition of "active", "retained", "activated"
  cohorts.py     retention, activation, breadth, Simpson's-paradox check
  pqa.py         product-qualified account scoring, reasons, plays, noise suppression
  motions.py     sales-trigger threshold and acquisition-channel ranking
  experiment.py  outreach holdout simulation: account vs user randomization
  tools.py       the functions the agent may call (testable without a model)
  agent.py       Strands agent on Amazon Bedrock
  report.py      charts and findings memo
evals/
  golden.json    golden questions with required facts, caveats and forbidden claims
  run_evals.py   grades the analysis, the rubric itself, and (optionally) the agent
```

**Two channels, one picture.** Self-serve users sign up with Google, Apple, GitHub, Amazon or email; enterprise users arrive through a corporate directory. Personal domains and Apple private-relay addresses can't be tied to a company, so only about 4 in 10 self-serve users resolve. That ceiling is reported, not hidden.

**Dhruva, the metric layer.** Named for the pole star you navigate by. Every number, whether in a chart or in an agent's answer, comes from one set of definitions, so "active user" means the same thing everywhere.

**Signal vs noise.** Account scores add transparent points for breadth across functions, scale, activation, recent activity, sharing and paid intent. A noise filter catches signup bursts that look like demand but aren't: most sign-ups in a single week, one function, low activation, like a webinar spike. Cohorts below 150 users are flagged as too small to act on.

**From signal to sales motion.** The trigger rule is searched over simple, explainable forms ("at least *k* activated users across at least *f* functions") and chosen by F1 against observed contracts, then compared with the sign-up-count rule most dashboards would use. Each account gets a play: route to an existing cloud account team, offer a team pilot through business development, enable champions in-product, alert a customer's admin to unmanaged adopters, or nurture without a sales touch.

**An agent you can check.** The agent can only call governed tools, and its instructions require sample sizes, external-only reporting, a within-segment check before crediting any feature, a named alternative explanation, and a confirming experiment. The eval rubric scores each answer on required facts, required caveats and forbidden claims, and the rubric is itself tested: a known-good answer must pass and a known-bad one must fail.

## Eval results

```
[analytics]
  PASS  Customer zero inflation detected
  PASS  Agent action beats question-only for activation
  PASS  3+ connectors retain better than 0-2
  PASS  Desktop app flagged as confounded (Simpson's trap)
  PASS  PQA precision@30 >= 0.8                       (0.87)
  PASS  No webinar-noise account in the top 30
  PASS  All webinar spikes flagged, no false flags     (12/12, 0 false)
  PASS  Account-level design recovers true lift
  PASS  User-level design underestimates (interference)
  PASS  Sales trigger recovers the planted tipping point (5 activated users)
  PASS  Activated-user trigger beats a sign-up-count trigger   (F1 0.62 vs 0.47)
  PASS  Teammate invites rank first on pipeline and retention
  PASS  Low-intent social channels rank in the bottom half on retention
[rubric_self_test]
  PASS  x5 golden questions: good answer passes, bad answer fails
18/18 checks passed
```

The rubric self-test earns its place: while adding the sales-trigger question, it caught the grader reading "5 activated users" as "5%" and failing a correct answer.

## Limits

- The sales trigger is fit on about 40 historical contracts. It recovered the planted tipping point (5 activated users) but loosened the planted 3-function requirement to 2, because nearly every company that reaches 5 activated users already spans 3 functions. With so few outcomes, refit it as contracts accumulate and by segment.
- Planted effects are deliberately clear. Real data is noisier, and thresholds (3+ functions, the 60-point score, the noise filter) are starting points to tune against real conversion outcomes.
- The activation finding is observational: high-intent users both act and stay. Only an experiment settles cause.
- Using a personal sign-up's activity to prompt outreach to their employer must respect the privacy terms users accepted and regional law. Self-serve individuals get in-product nudges, not sales calls.

## License

MIT. Built by Rahul Kamath.
