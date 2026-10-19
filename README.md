# Sangam: growth signals for an AI workspace product

**Sangam** (Sanskrit: *confluence*) is where independent streams meet and become one river. In product-led growth, the streams are individual adopters who sign up on their own and the enterprise rollouts that follow. This project finds where they converge.

It is an agentic growth-analytics prototype that:

- ties self-serve sign-ups to companies, and says honestly when it can't,
- runs cohort and retention analysis that handles the classic traps,
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

Five findings, each verified against a known planted answer ([full memo](reports/findings.md)).

**1. Activation is the first agent action, not the first question.** External users who complete an agent action in week 0 retain at about three times the rate of question-only users at week 8. The gap holds in every segment. It is observational, so the recommended next step is an onboarding experiment.

![Retention by week-0 behavior](reports/retention_by_activation.png)

**2. Customer zero flatters every headline.** A large internal deployment with mandated use lifts week-8 retention from 27% to 33%. External users are always reported separately.

**3. Breadth predicts retention.** Users who link three or more connectors in week 0 retain far better than those who link one or two.

**4. Not every lift is real.** Desktop-app users retain 20 points better in aggregate, and about 0 points better inside every segment. The internal rollout installed the app by default, so the aggregate is a mix effect (Simpson's paradox). The analysis flags it automatically.

![Desktop app lift disappears within segments](reports/desktop_simpson.png)

**5. Test sales plays at the account level.** In a collaboration product, colleagues share the outcome of outreach. Splitting users inside a company leaks treatment into the control group and understates the lift; randomizing whole accounts recovers it.

![Experiment design comparison](reports/experiment_design.png)

## How it works

```
sangam/
  generate.py    synthetic users, accounts, events, with planted effects and noise
  identity.py    resolve self-serve users to companies by email domain
  dhruva.py      the governed metric layer: one definition of "active", "retained", "activated"
  cohorts.py     retention, activation, breadth, Simpson's-paradox check
  pqa.py         product-qualified account scoring, reasons, plays, noise suppression
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

**From signal to sales motion.** Each account gets a play: route to an existing cloud account team, offer a team pilot through business development, enable champions in-product, alert a customer's admin to unmanaged adopters, or nurture without a sales touch.

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
[rubric_self_test]
  PASS  x4 golden questions: good answer passes, bad answer fails
13/13 checks passed
```

## Limits

- Planted effects are deliberately clear. Real data is noisier, and thresholds (3+ functions, the 60-point score, the noise filter) are starting points to tune against real conversion outcomes.
- The activation finding is observational: high-intent users both act and stay. Only an experiment settles cause.
- Using a personal sign-up's activity to prompt outreach to their employer must respect the privacy terms users accepted and regional law. Self-serve individuals get in-product nudges, not sales calls.

## License

MIT. Built by Rahul Kamath.
