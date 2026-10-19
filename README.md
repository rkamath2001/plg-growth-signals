# Sangam: growth signals for an AI workspace product

**Sangam** (Sanskrit: *confluence*) is where independent streams meet and become one river. In product-led growth, the streams are individual adopters who sign up on their own, the colleagues they share with, and the enterprise rollouts that follow. This project finds where they converge.

> **All data is synthetic.** The product modeled is a generic AI workspace (an assistant that answers questions, takes agent actions, shares agents and outputs, and connects to apps), described from public information only. Company names and `.example` domains are invented. Nothing here reflects any company's internal data.

## In 60 seconds

- **Activation is the first agent action.** Users who complete one in their first week retain at 45% at week 8, versus 15% for those who only ask questions.
- **Start an enterprise sales motion at 5+ activated independent users at a company**, not at a sign-up count: those companies convert at 60% versus a 16% baseline. At 4 users, run champion enablement instead.
- **Shared agents are the strongest viral loop; shared assets are the landing loop** that seeds new companies. Embeds and digests barely convert.
- **Pay sharing rewards when the recipient completes a first agent action, and tie them to the account's stage**: same-company shares before a contract, external shares after it. In simulation that keeps the same pipeline gains as uniform rewards while paying 1,335 rewards instead of 12,509.
- **Visibility is the hidden constraint.** Apple and Amazon sign-ins almost never reveal a company. Connected Slack, Teams and Jira workspaces help, but only with guards: naive matching is 67% accurate and invents sales-ready accounts from school clubs and side projects.
- **Everything is graded**: 32 of 32 checks pass against planted ground truth, including tests of the grader itself.

## Quick start

```bash
pip install -r requirements.txt
python run.py                 # generate data, analyze, grade, write reports/ and this README
python -m evals.run_evals     # grade the analysis against the planted ground truth
```

The agent is optional and needs AWS credentials with Amazon Bedrock model access:

```bash
export AWS_REGION=us-west-2            # optional: SANGAM_MODEL_ID=<bedrock model id>
python -m sangam.agent "Which accounts should business development contact this week, and why?"
python -m evals.run_evals --agent      # grade the agent's answers to the golden questions
```

## Findings

Each finding is checked against a planted answer. The [findings memo](reports/findings.md) has the detail.

### 1. Activation is the first agent action, not the first question

External users who complete an agent action in their first week retain at 45% at week 8, versus 15% for question-only users, and the gap holds in every segment. It's observational: high-intent users both act and stay, so the next step is an onboarding experiment that nudges a first agent action.

![Retention by week-0 behavior](reports/retention_by_activation.png)

### 2. Customer zero flatters every headline

A large internal deployment with mandated use lifts week-8 retention from 27% to 33%. External users are always reported separately.

### 3. Breadth predicts retention

Users who link three or more connectors in their first week retain at 49%, versus 19% for one or two.

### 4. Not every lift is real

Desktop-app users retain +18% better in aggregate and about -0% inside every segment. The internal rollout installed the app by default, so the aggregate is a mix effect (Simpson's paradox), and the analysis flags it automatically.

![Desktop app lift disappears within segments](reports/desktop_simpson.png)

### 5. Test sales plays at the account level

Colleagues share the outcome of outreach. Splitting users inside a company leaks treatment into the control group: in simulation it reports +1.6% against a true lift of +4.0%, while randomizing whole accounts recovers +3.9%.

![Experiment design comparison](reports/experiment_design.png)

### 6. Start the sales motion at 5 activated adopters

Learned from 139 observed contracts. Companies with 5+ independent users who completed an agent action convert at 60% versus a 16% baseline (3.7x). At exactly 4 they convert at 23%, a champion-enablement tier; below that, at 4%. The best rule built on raw sign-up counts scores F1 0.50 against 0.64, because event spikes inflate sign-ups without activating.

![Sales trigger threshold](reports/sales_trigger_threshold.png)

3 candidate rules are statistically tied (5+ users across 1+ functions, 5+ users across 2+ functions, 5+ users across 3+ functions), so the method bootstraps F1, treats everything within one standard error of the best as a tie, and picks the simplest. A plain "highest F1" search once chose "1+ users across 4+ functions": technically equivalent to 4 users across 4 functions, but nonsense to a seller.

### 7. Rank acquisition channels by pipeline, not volume

Rankings disagree. 'search' brings the most sign-ups, but 'linkedin' produces the most sales-ready accounts per 1,000 sign-ups (26.6) and retains 22% at week 8. 'webinar' and 'reddit' retain worst. Invest in invite loops and work-identity channels for pipeline; judge broad social channels on retained users, not sign-ups. Pipeline ranks for 'webinar' rest on fewer than 5 accounts; treat that rank as noise.

| Channel | Sign-ups | Activation | Week-8 retention | Resolved to a company | Sales-ready accounts per 1,000 | Rank: volume / retention / pipeline |
|---|---|---|---|---|---|---|
| linkedin | 1,429 | 46% | 22% | 61% | 26.6 | 2 / 2 / 1 |
| teammate_invite | 1,157 | 54% | 27% | 63% | 21.6 | 6 / 1 / 2 |
| direct | 1,151 | 40% | 18% | 37% | 17.4 | 7 / 4 / 3 |
| search | 1,976 | 41% | 19% | 38% | 14.2 | 1 / 3 / 4 |
| youtube | 1,231 | 37% | 18% | 26% | 8.9 | 5 / 5 / 5 |
| x | 1,314 | 35% | 16% | 19% | 8.4 | 3 / 6 / 6 |
| reddit | 1,281 | 31% | 13% | 14% | 7.8 | 4 / 7 / 7 |
| webinar | 290 | 11% | 1% | 90% | 6.9 | 8 / 8 / 8 |

**Attribution warning.** Viral-loop recipients are 47% of the activated users at sales-ready accounts but get first-touch credit for only 7% of those accounts. First-touch attribution undervalues expansion loops by design, so loops are measured separately, on the prospects they push over the sales trigger.

### 8. Sign-in provider decides who you can see

Provider decides visibility more than quality. 54% of Google and 61% of email sign-ups can be tied to a company, versus 2% for 'amazon' and 9% for 'apple'. 'google' users retain best (22%), consistent with a builder persona. The pipeline ranking mostly mirrors visibility: an account you cannot see never reaches the sales trigger.

| Provider | Sign-ups | Activation | Week-8 retention | Resolved to a company | Private relay | Users at sales-ready accounts per 1,000 | Rank: volume / retention / visibility / pipeline |
|---|---|---|---|---|---|---|---|
| email | 2,969 | 42% | 21% | 61% | 0% | 190.6 | 2 / 2 / 1 / 1 |
| google | 6,921 | 45% | 22% | 54% | 0% | 169.1 | 1 / 1 / 2 / 2 |
| github | 1,539 | 47% | 20% | 32% | 0% | 91.0 | 4 / 3 / 3 / 3 |
| apple | 2,351 | 40% | 19% | 9% | 60% | 28.1 | 3 / 4 / 4 / 4 |
| amazon | 1,155 | 41% | 17% | 2% | 0% | 8.7 | 5 / 5 / 5 / 5 |

876 self-serve users at prospect companies are invisible today, mostly via apple, github sign-ins. If 30% added a work email, about 15 more companies would cross the sales trigger, on top of 156 visible today; with full visibility, 52 more would. A 'connect your work email to share with your team' prompt is a pipeline lever, not just an identity feature. *(Simulation on synthetic ground truth; real uptake must be measured with an A/B test of the prompt.)*

### 9. Connected workspaces reveal employers, with guards against false positives

People connect their employer's Slack, Teams or Jira, but also their kid's robotics team Slack, hobby groups, big open communities, and clients' workspaces as contractors, and some of those share a company's name.

| Matcher | Users attributed | Precision | Hidden employees recovered | Sales-ready accounts (correct / phantom) |
|---|---|---|---|---|
| Work email only | - | - | - | 156 / 0 |
| Naive connector match | 632 | 67% | 44% | 184 / 3 |
| Guarded connector match | 329 | 100% | 34% | 175 / 0 |

Naive matching attributes 632 hidden users at 67% precision and creates 3 phantom sales-ready accounts. The worst naive error: 'Arworth Hiking Club' put 18 unrelated users into Arworth Retail. Guarded matching attributes 329 at 100% precision, recovers 34% of hidden employees, and adds 19 genuinely sales-ready accounts with 0 phantoms. Trust a workspace's verified domain; treat names as clues that need a colleague to corroborate them; drop guests and any workspace whose members already resolve to several companies. Synthetic data makes the guards look perfect; in production, audit a sample of attributions by hand each quarter.

The guarded matcher trusts verified domains; treats a matching name as a clue that needs a colleague resolved by work email to corroborate it; drops guest memberships; drops workspaces whose connected users already resolve to 3+ companies, the signature of a school club; skips users whose evidence points to two companies; and never overrides a work email. Workspace metadata is personal context: use it only in aggregate at the account level, within the permissions users granted, and never to contact an individual about a side project.

### 10. Viral loops: agent shares grow, asset shares land, rewards must fire on activation

'Shared agent' grows the product most (3.26 activated recipients per 100 users; 56% of its sign-ups activate) and turns fastest. 'Shared asset (URL)' is the landing loop: it seeds the most new companies (51). 'Shared space / knowledge base' recipients retain best. Embeds and digests create many impressions but convert under 3% per share, and referral credits paid on sign-up bring sign-ups of which only 24% activate. In the reward simulation, paying per share sent nearly doubles shares but adds only +262 activated users. The stage-aware policy delivers the same pipeline as uniform weighted rewards (5.4 vs 5.4 extra prospects over the trigger; 3.7 vs 3.7 companies seeded by customers) while paying 1,335 rewards instead of 12,509. Uniform rewards buy more total sign-ups, mostly prosumer activity and colleagues who were already licensed.

![Viral loops](reports/viral_loops.png)

| Loop | Shares | Sign-up per share | Sign-ups that activate | Activated recipients per 100 users | Median days to sign-up | Recipient week-8 retention | Companies seeded | Prospects pushed over trigger |
|---|---|---|---|---|---|---|---|---|
| Shared agent | 9,785 | 34.5% | 56% | 3.26 | 2 | 30% | 26 | 53 |
| Shared asset (URL) | 13,361 | 17.2% | 47% | 3.08 | 4.5 | 24% | 51 | 64 |
| Shared space / knowledge base | 5,309 | 39.9% | 63% | 2.14 | 7 | 38% | 9 | 44 |
| Recurring digest | 13,726 | 2.7% | 35% | 0.34 | 17 | 18% | 5 | 4 |
| Slack or email embed | 26,068 | 1.4% | 46% | 0.31 | 13 | 26% | 3 | 8 |
| Referral credit | 1,236 | 19.5% | 24% | 0.2 | 3 | 10% | 1 | 2 |

**Reward policy simulation.** Six ways to reward sharing, on the same population:

| Reward fires... | Shares | Extra activated users | Rewards paid | Rewards per extra activated user | Extra prospects over trigger | Extra companies seeded by customers |
|---|---|---|---|---|---|---|
| No reward (status quo) | 69,485 | +0 | 0 | - | 0.0 | 0.0 |
| Per share sent | 125,073 | +262 | 125,073 | 477.38 | 1.6 | 1.3 |
| Per recipient sign-up | 97,279 | +472 | 6,025 | 12.76 | 2.9 | 2.3 |
| Per recipient first agent action | 86,856 | +590 | 12,219 | 20.71 | 3.7 | 2.9 |
| Per first agent action, weighted by share type | 84,876 | +751 | 12,509 | 16.66 | 5.4 | 3.7 |
| Stage-aware (see below) | 73,213 | +292 | 1,335 | 4.57 | 5.4 | 3.7 |

The **stage-aware** policy pays on the recipient's first agent action, weights agent and space shares higher, rewards *same-company* shares before a company has a contract (each activated colleague moves it toward the sales trigger), rewards *external* shares to customers and partners after a contract (customers become a distribution channel), and never pays for colleagues who are already licensed. Paying per share sent nearly doubles shares (125,073) for the smallest gain in activated users.

Viral coefficients are single-generation. The reward simulation rests on stated behavioral assumptions (see ASSUMPTIONS in sangam/loops.py); test the policy with an A/B test, randomized by workspace, before rolling it out.

## How it works

```
sangam/
  generate.py    synthetic users, accounts, events, shares, workspaces; planted effects and noise
  identity.py    resolve self-serve users to companies by email domain
  dhruva.py      the governed metric layer: one definition of "active", "retained", "activated"
  cohorts.py     retention, activation, breadth, Simpson's-paradox check
  pqa.py         product-qualified account scoring, reasons, plays, noise suppression
  motions.py     sales trigger, channel and sign-in provider rankings, work-email what-if
  connectors.py  naive vs guarded identity from connected Slack, Teams and Jira workspaces
  loops.py       viral loop scorecard, expand vs land, reward policy simulation
  experiment.py  outreach holdout simulation: account vs user randomization
  tools.py       the functions the agent may call (testable without a model)
  agent.py       Strands agent on Amazon Bedrock
  report.py      charts and findings memo;  readme.py renders this README from the results
evals/
  golden.json    golden questions with required facts, caveats and forbidden claims
  run_evals.py   grades the analysis, the rubric itself, and (optionally) the agent
```

**Dhruva, the metric layer.** Named for the pole star you navigate by. Every number, in a chart or in an agent's answer, comes from one set of definitions.

**An agent you can check.** The agent can only call governed tools. Its instructions require sample sizes, external-only reporting, a within-segment check before crediting any feature, a named alternative explanation, and a confirming experiment. The eval rubric scores each answer on required facts, required caveats and forbidden claims, and the rubric is itself tested: a known-good answer must pass and a known-bad one must fail. That self-test once caught the grader reading "5 activated users" as "5%" and failing a correct answer.

## Eval results

```
[analytics]
  PASS  Customer zero inflation detected
  PASS  Agent action beats question-only for activation
  PASS  3+ connectors retain better than 0-2
  PASS  Desktop app flagged as confounded (Simpson's trap)
  PASS  PQA precision@30 >= 0.8
  PASS  No webinar-noise account in the top 30
  PASS  All webinar spikes flagged, no false flags
  PASS  Account-level design recovers true lift (within 1.5 pts)
  PASS  User-level design underestimates (interference)
  PASS  Sales trigger recovers the planted tipping point (5 activated users)
  PASS  Activated-user trigger beats a sign-up-count trigger
  PASS  Teammate invites retain best; invites and LinkedIn lead on pipeline
  PASS  Low-intent social channels rank in the bottom half on retention
  PASS  Google and email are the most visible providers; Apple and Amazon the least
  PASS  Making hidden adopters visible adds sales-ready accounts
  PASS  Naive connector matching produces false positives
  PASS  Guarded connector matching is precise and adds real sales-ready accounts
  PASS  Community and side-project workspaces are the main false-positive source
  PASS  Shared agents have the highest viral coefficient on activated users
  PASS  Shared spaces retain recipients best
  PASS  Shared assets seed the most new companies
  PASS  Embeds and digests convert worst per share
  PASS  Referral sign-ups activate least
  PASS  Rewarding shares sent maximizes shares but not activated users
  PASS  Stage-aware rewards keep the pipeline gains at a fraction of the cost
[rubric_self_test]
  PASS  Rubric separates good from bad answer: activation-definition
  PASS  Rubric separates good from bad answer: headline-retention
  PASS  Rubric separates good from bad answer: desktop-app
  PASS  Rubric separates good from bad answer: sales-targets
  PASS  Rubric separates good from bad answer: sales-trigger
  PASS  Rubric separates good from bad answer: connector-identity
  PASS  Rubric separates good from bad answer: reward-policy
32/32 checks passed
```

## Limits

- Planted effects are deliberately clear; real data is noisier. Thresholds are starting points to tune against real outcomes.
- The sales trigger is fit on 139 contracts, so several rules tie; refit it as contracts accumulate and by segment.
- Activation and channel findings are observational. Only experiments settle cause.
- The reward simulation rests on stated behavioral assumptions (`ASSUMPTIONS` in `sangam/loops.py`); its value is the measurement design. Viral coefficients are single-generation.
- Using a personal sign-up's activity or workspace metadata to prompt outreach must respect the permissions users granted and regional law. Individuals get in-product nudges, not sales calls.

## License

MIT. Built by Rahul Kamath.
