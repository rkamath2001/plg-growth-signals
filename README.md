# Sangam: growth signals for an AI workspace product

**Sangam** (Sanskrit: *confluence*) is where independent streams meet and become one river. In product-led growth, the streams are individual adopters who sign up on their own and the enterprise rollouts that follow. This project finds where they converge.

It is an agentic growth-analytics prototype that:

- ties self-serve sign-ups to companies, and says honestly when it can't,
- runs cohort and retention analysis that handles the classic traps,
- ranks **acquisition channels** by volume, retention and pipeline, which give different answers,
- learns **how many independent freemium adopters a company needs** before an enterprise sales motion pays off,
- shows how **sign-in providers** (Google, email, GitHub, Apple, Amazon) decide whether you can see the company at all,
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

Eight findings, each verified against a known planted answer ([full memo](reports/findings.md)).

**1. Activation is the first agent action, not the first question.** External users who complete an agent action in week 0 retain at about three times the rate of question-only users at week 8. The gap holds in every segment. It is observational, so the recommended next step is an onboarding experiment.

![Retention by week-0 behavior](reports/retention_by_activation.png)

**2. Customer zero flatters every headline.** A large internal deployment with mandated use lifts week-8 retention from 27% to 33%. External users are always reported separately.

**3. Breadth predicts retention.** Users who link three or more connectors in week 0 retain far better than those who link one or two.

**4. Not every lift is real.** Desktop-app users retain 20 points better in aggregate, and about 0 points better inside every segment. The internal rollout installed the app by default, so the aggregate is a mix effect (Simpson's paradox). The analysis flags it automatically.

![Desktop app lift disappears within segments](reports/desktop_simpson.png)

**5. Test sales plays at the account level.** In a collaboration product, colleagues share the outcome of outreach. Splitting users inside a company leaks treatment into the control group and understates the lift; randomizing whole accounts recovers it.

![Experiment design comparison](reports/experiment_design.png)

**6. Start the enterprise sales motion at 5 activated adopters, not at a sign-up count.** Learned from 47 observed contracts. Companies with 5+ independent users who completed an agent action convert at 63%, versus a 6% baseline (11x); at exactly 4 they convert at 26%, which is a champion-enablement tier, not a sales one; below 4 they convert at 2%. Requiring breadth across functions did not beat the simple count within noise. The best rule built on raw sign-up counts does markedly worse (F1 0.42 vs 0.54), because event spikes inflate sign-ups without activating.

![Sales trigger threshold](reports/sales_trigger_threshold.png)

With this few contracts, eight candidate rules are statistically tied (all at 4 or 5 activated users), so the method bootstraps F1, treats everything within one standard error of the best as a tie, and picks the simplest rule. A plain "pick the highest F1" search chose "1+ users across 4+ functions" on one data draw: a rule that is technically equivalent to 4 users across 4 functions but reads as nonsense to a seller.

**7. Rank acquisition channels by pipeline, not volume.** Search brings the most sign-ups; teammate invites rank 6th on volume but 1st on both retention and sales-ready accounts per 1,000 sign-ups, with LinkedIn second because work identities resolve to companies. X and Reddit bring volume that rarely retains or resolves.

| Channel | Sign-ups | Activation | Week-8 retention | Resolved to a company | Sales-ready accounts per 1,000 | Rank: volume / retention / pipeline |
|---|---|---|---|---|---|---|
| teammate_invite | 1,157 | 54% | 27% | 63% | 10.4 | 6 / 1 / 1 |
| linkedin | 1,429 | 46% | 22% | 61% | 6.3 | 2 / 2 / 2 |
| webinar | 290 | 11% | 1% | 90% | 3.4 | 8 / 8 / 3 |
| search | 1,976 | 41% | 19% | 38% | 2.5 | 1 / 3 / 4 |
| direct | 1,151 | 40% | 18% | 37% | 1.7 | 7 / 4 / 5 |
| reddit | 1,281 | 31% | 13% | 14% | 1.6 | 4 / 7 / 6 |
| youtube | 1,231 | 37% | 18% | 26% | 1.6 | 5 / 5 / 6 |
| x | 1,314 | 35% | 16% | 19% | 1.5 | 3 / 6 / 8 |

Pipeline ranks below the top two rest on fewer than 5 accounts each (webinar's third place is a single account), so treat their order as noise. Accounts are credited to the channel of their first sign-up (first-touch); that choice is stated so it can be challenged, and budget shifts should be confirmed with geo or time holdouts.

**8. Sign-in provider decides who you can see.** Provider is an identity channel, not an acquisition channel. Half of Google and 58% of work-email sign-ups can be tied to a company; Apple's private relay hides 60% of its users and Amazon sign-ins reveal a company 1% of the time. GitHub users retain slightly best, consistent with a builder persona, but provider differences in retention are small. The pipeline ranking mirrors visibility: an account you cannot see never reaches the sales trigger.

| Provider | Sign-ups | Activation | Week-8 retention | Resolved to a company | Private relay | Users at sales-ready accounts per 1,000 | Rank: volume / retention / visibility / pipeline |
|---|---|---|---|---|---|---|---|
| email | 1,902 | 39% | 19% | 58% | 0% | 84.6 | 2 / 2 / 1 / 1 |
| google | 4,505 | 41% | 19% | 50% | 0% | 69.9 | 1 / 3 / 2 / 2 |
| github | 1,017 | 45% | 20% | 29% | 0% | 35.4 | 4 / 1 / 3 / 3 |
| apple | 1,631 | 35% | 17% | 9% | 60% | 8.0 | 3 / 4 / 4 / 4 |
| amazon | 774 | 38% | 16% | 1% | 0% | 3.9 | 5 / 5 / 5 / 5 |

A what-if on the synthetic ground truth: 417 adopters at prospect companies are invisible today, mostly through Apple and GitHub sign-ins. Full visibility would put 11 more companies over the sales trigger (on top of 35); a work-email prompt with 30% uptake would add about 3. That makes "connect your work email to share with your team" a pipeline lever, and its real uptake is an A/B test away.

## How it works

```
sangam/
  generate.py    synthetic users, accounts, events, with planted effects and noise
  identity.py    resolve self-serve users to companies by email domain
  dhruva.py      the governed metric layer: one definition of "active", "retained", "activated"
  cohorts.py     retention, activation, breadth, Simpson's-paradox check
  pqa.py         product-qualified account scoring, reasons, plays, noise suppression
  motions.py     sales-trigger threshold, channel and sign-in provider rankings, work-email what-if
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
  PASS  Activated-user trigger beats a sign-up-count trigger   (F1 0.54 vs 0.42)
  PASS  Teammate invites rank first on pipeline and retention
  PASS  Low-intent social channels rank in the bottom half on retention
  PASS  Google and email are the most visible providers; Apple and Amazon the least
  PASS  Making hidden adopters visible adds sales-ready accounts
[rubric_self_test]
  PASS  x5 golden questions: good answer passes, bad answer fails
20/20 checks passed
```

The rubric self-test earns its place: while adding the sales-trigger question, it caught the grader reading "5 activated users" as "5%" and failing a correct answer.

## Limits

- The sales trigger is fit on 47 historical contracts, so several rules tie; the simplest is chosen and the tie is reported. The planted rule also required 3+ functions, which the data could not distinguish from the count alone. Refit as contracts accumulate and by segment.
- Planted effects are deliberately clear. Real data is noisier, and thresholds (3+ functions, the 60-point score, the noise filter) are starting points to tune against real conversion outcomes.
- The activation finding is observational: high-intent users both act and stay. Only an experiment settles cause.
- Using a personal sign-up's activity to prompt outreach to their employer must respect the privacy terms users accepted and regional law. Self-serve individuals get in-product nudges, not sales calls.

## License

MIT. Built by Rahul Kamath.
