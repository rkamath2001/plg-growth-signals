# Findings memo: growth signals for an AI workspace product

*All data is synthetic, generated with a fixed seed. Effects were planted so every finding can be checked against a known answer.*

## Summary

Nine findings, each checked against planted ground truth (see `evals/`):

1. **Report external users separately.** Customer zero raises week-8 retention from 27% to 33%. Internal use is mandated, so it flatters every headline it touches.
2. **Activation is the first agent action.** External users who complete one in week 0 retain at 45% at week 8, versus 15% for question-only users (95% CI +29% to +31%), and the gap holds in every segment. This is observational; the next step is an onboarding experiment that nudges a first agent action.
3. **Breadth predicts retention.** Users linking 3+ connectors in week 0 retain at 49%, versus 19% for 1-2. Make the third connector a guided onboarding step.
4. **Don't credit the desktop app.** Its aggregate lift of +19% shrinks to -0% inside each segment. The internal rollout installed it by default.
5. **Test sales plays by account.** In simulation, randomizing accounts recovers the true lift (+4.3% vs +4.3%); splitting users inside a company reports +1.8%.
6. **Trigger sales on activated adopters, not sign-ups.** Companies with 5+ activated independent users convert at 63%, 11.2x the 6% baseline.
7. **Rank channels by pipeline, not volume.** The top channel by sign-ups is not the top channel by sales-ready accounts; teammate invites lead on retention and pipeline.
8. **Sign-in provider decides visibility.** Google and work-email sign-ups reveal the company about half the time; Apple and Amazon almost never. A work-email prompt at the moment of sharing would put more companies over the sales trigger.
9. **Connected workspaces reveal employers, if guarded.** Matching Slack, Teams and Jira workspaces naively invents adopters from school clubs, side projects and client workspaces; trusting verified domains and requiring corroboration for names recovers real sales-ready accounts with no phantoms.

## When to start an enterprise sales motion

Start an enterprise sales motion at 5+ activated independent users. Those companies convert at 63% versus a 6% baseline (11.2x); the rule captures 47% of contracts while flagging 35 accounts. At 4 activated users conversion is 26%: run champion enablement there, not sales. Requiring a minimum number of functions did not beat the simple count within noise. The best sign-up-count rule scores F1 0.42 against 0.54, because sign-ups include event spikes that never activate.

![Sales trigger threshold](sales_trigger_threshold.png)

Fit on 47 contracts: 8 rules are statistically tied, so the simplest was chosen. Counts only users resolvable to a company by email domain, so the true number of adopters is higher. Refit each quarter and by segment as outcomes accumulate.

## Which acquisition channels matter

Rankings disagree. 'search' brings the most sign-ups, but 'teammate_invite' produces the most sales-ready accounts per 1,000 sign-ups (10.4) and retains 27% at week 8. 'webinar' and 'reddit' retain worst. Invest in invite loops and work-identity channels for pipeline; judge broad social channels on retained users, not sign-ups. Pipeline ranks for 'webinar', 'direct', 'reddit', 'youtube', 'x' rest on fewer than 5 accounts each; treat their order as noise.

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

*Attribution: first-touch at the account level; last-touch at the user level. Channels and intent are entangled: invited users arrive with a colleague's context. Test channel spend with geo or time holdouts before reallocating budget.*

## Sign-in providers: who can we see?

Provider decides visibility more than quality. 50% of Google and 58% of email sign-ups can be tied to a company, versus 1% for 'amazon' and 9% for 'apple'. 'github' users retain best (20%), consistent with a builder persona. The pipeline ranking mostly mirrors visibility: an account you cannot see never reaches the sales trigger.

| Provider | Sign-ups | Activation | Week-8 retention | Resolved to a company | Private relay | Users at sales-ready accounts per 1,000 | Rank: volume / retention / visibility / pipeline |
|---|---|---|---|---|---|---|---|
| email | 1,902 | 39% | 19% | 58% | 0% | 84.6 | 2 / 2 / 1 / 1 |
| google | 4,505 | 41% | 19% | 50% | 0% | 69.9 | 1 / 3 / 2 / 2 |
| github | 1,017 | 45% | 20% | 29% | 0% | 35.4 | 4 / 1 / 3 / 3 |
| apple | 1,631 | 35% | 17% | 9% | 60% | 8.0 | 3 / 4 / 4 / 4 |
| amazon | 774 | 38% | 16% | 1% | 0% | 3.9 | 5 / 5 / 5 / 5 |

Provider retention differences are small and partly persona mix; do not steer users between sign-in options on retention alone.

**What if hidden adopters added a work email?** 417 self-serve users at prospect companies are invisible today, mostly via apple, github sign-ins. If 30% added a work email, about 3 more companies would cross the sales trigger, on top of 35 visible today; with full visibility, 11 more would. A 'connect your work email to share with your team' prompt is a pipeline lever, not just an identity feature. *(Simulation on synthetic ground truth; real uptake must be measured with an A/B test of the prompt.)*

## Connected workspaces as identity evidence

Naive matching attributes 441 hidden users at 52% precision and creates 6 phantom sales-ready accounts. The worst naive error: 'Fenton Hiking Club' put 21 unrelated users into Fenton Group. Guarded matching attributes 176 at 100% precision, recovers 35% of hidden employees, and adds 6 genuinely sales-ready accounts with 0 phantoms. Trust a workspace's verified domain; treat names as clues that need a colleague to corroborate them; drop guests and any workspace whose members already resolve to several companies. Synthetic data makes the guards look perfect; in production, audit a sample of attributions by hand each quarter.

| Matcher | Users attributed | Precision | Hidden employees recovered | Sales-ready accounts (correct / phantom) |
|---|---|---|---|---|
| Work email only | - | - | - | 35 / 0 |
| Naive connector match | 441 | 52% | 46% | 41 / 6 |
| Guarded connector match | 176 | 100% | 35% | 41 / 0 |

Naive errors by the guard that blocks them: community or side-project workspace: 191; guest in another company's workspace: 10; name-stem match without a corroborating colleague: 10. Workspace metadata is personal context: use it only in aggregate at the account level, within the permissions users granted, and never to contact an individual about a side project.

## Product-qualified accounts this week

Independent adopters at non-customers, scored with reasons. Signup spikes with low activation are suppressed as noise.

| Company | Score | Play | Why |
|---|---|---|---|
| Torgate Retail | 101 | Route to existing cloud account team: propose an enterprise pilot | 22 independent users across 5 functions; 82% completed an agent action in week 0; 55% active in the last 4 weeks; 13 shared agents with colleagues; 4 on a paid plan |
| Fenmont Holdings | 100 | Business development: offer a team pilot with admin controls | 11 independent users across 6 functions; 100% completed an agent action in week 0; 73% active in the last 4 weeks; 6 shared agents with colleagues; 3 on a paid plan |
| Verworth Holdings | 99 | Route to existing cloud account team: propose an enterprise pilot | 24 independent users across 6 functions; 83% completed an agent action in week 0; 42% active in the last 4 weeks; 14 shared agents with colleagues; 6 on a paid plan |
| Jorholm Systems | 98 | Route to existing cloud account team: propose an enterprise pilot | 18 independent users across 6 functions; 78% completed an agent action in week 0; 56% active in the last 4 weeks; 10 shared agents with colleagues; 5 on a paid plan |
| Arford Industries | 97 | Business development: offer a team pilot with admin controls | 19 independent users across 6 functions; 79% completed an agent action in week 0; 42% active in the last 4 weeks; 8 shared agents with colleagues; 4 on a paid plan |
| Rosridge Retail | 97 | Route to existing cloud account team: propose an enterprise pilot | 21 independent users across 6 functions; 76% completed an agent action in week 0; 38% active in the last 4 weeks; 11 shared agents with colleagues; 5 on a paid plan |
| Jorora Health | 96 | Business development: offer a team pilot with admin controls | 19 independent users across 5 functions; 74% completed an agent action in week 0; 42% active in the last 4 weeks; 6 shared agents with colleagues; 4 on a paid plan |
| Torgate Labs | 96 | Business development: offer a team pilot with admin controls | 20 independent users across 6 functions; 70% completed an agent action in week 0; 40% active in the last 4 weeks; 7 shared agents with colleagues; 6 on a paid plan |

## What would change these conclusions

- An onboarding experiment showing that nudging an agent action does *not* lift retention would mean the activation gap is intent, not cause.
- If identity resolution improves (fewer private-relay and personal addresses), account scores will shift; today about 4 in 10 self-serve users can be tied to a company.
- The sales trigger is fit on a few dozen historical contracts; several rules tie, so refit it as outcomes accumulate, and expect it to move by segment and company size.
- Thresholds (3+ functions, 60-point score, noise filter) are starting points to tune against real conversion outcomes.
