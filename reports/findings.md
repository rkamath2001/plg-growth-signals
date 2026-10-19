# Findings memo: growth signals for an AI workspace product

*All data is synthetic, generated with a fixed seed. Effects were planted so every finding can be checked against a known answer.*

## Summary

Ten findings, each checked against planted ground truth (see `evals/`):

1. **Report external users separately.** Customer zero raises week-8 retention from 27% to 33%. Internal use is mandated, so it flatters every headline it touches.
2. **Activation is the first agent action.** External users who complete one in week 0 retain at 45% at week 8, versus 15% for question-only users (95% CI +29% to +31%), and the gap holds in every segment. This is observational; the next step is an onboarding experiment that nudges a first agent action.
3. **Breadth predicts retention.** Users linking 3+ connectors in week 0 retain at 49%, versus 19% for 1-2. Make the third connector a guided onboarding step.
4. **Don't credit the desktop app.** Its aggregate lift of +18% shrinks to -0% inside each segment. The internal rollout installed it by default.
5. **Test sales plays by account.** In simulation, randomizing accounts recovers the true lift (+3.9% vs +4.0%); splitting users inside a company reports +1.6%.
6. **Trigger sales on activated adopters, not sign-ups.** Companies with 5+ activated independent users convert at 60%, 3.7x the 16% baseline.
7. **Rank channels by pipeline, not volume.** The top channel by sign-ups is not the top channel by sales-ready accounts; teammate invites lead on retention and pipeline.
8. **Sign-in provider decides visibility.** Google and work-email sign-ups reveal the company about half the time; Apple and Amazon almost never. A work-email prompt at the moment of sharing would put more companies over the sales trigger.
9. **Connected workspaces reveal employers, if guarded.** Matching Slack, Teams and Jira workspaces naively invents adopters from school clubs, side projects and client workspaces; trusting verified domains and requiring corroboration for names recovers real sales-ready accounts with no phantoms.
10. **Agent shares grow, asset shares land; reward activation, by account stage.** Paying per share sent buys shares, not users; a stage-aware policy paid on the recipient's first agent action keeps the pipeline gains at a fraction of the cost.

## When to start an enterprise sales motion

Start an enterprise sales motion at 5+ activated independent users. Those companies convert at 60% versus a 16% baseline (3.7x); the rule captures 68% of contracts while flagging 156 accounts. At 4 activated users conversion is 23%: run champion enablement there, not sales. Requiring a minimum number of functions did not beat the simple count within noise. The best sign-up-count rule scores F1 0.50 against 0.64, because sign-ups include event spikes that never activate.

![Sales trigger threshold](sales_trigger_threshold.png)

Fit on 139 contracts: 3 rules are statistically tied, so the simplest was chosen. Counts only users resolvable to a company by email domain, so the true number of adopters is higher. Refit each quarter and by segment as outcomes accumulate.

## Which acquisition channels matter

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

*Attribution: first-touch at the account level; last-touch at the user level. Channels and intent are entangled: invited users arrive with a colleague's context. Test channel spend with geo or time holdouts before reallocating budget.*

## Sign-in providers: who can we see?

Provider decides visibility more than quality. 54% of Google and 61% of email sign-ups can be tied to a company, versus 2% for 'amazon' and 9% for 'apple'. 'google' users retain best (22%), consistent with a builder persona. The pipeline ranking mostly mirrors visibility: an account you cannot see never reaches the sales trigger.

| Provider | Sign-ups | Activation | Week-8 retention | Resolved to a company | Private relay | Users at sales-ready accounts per 1,000 | Rank: volume / retention / visibility / pipeline |
|---|---|---|---|---|---|---|---|
| email | 2,969 | 42% | 21% | 61% | 0% | 190.6 | 2 / 2 / 1 / 1 |
| google | 6,921 | 45% | 22% | 54% | 0% | 169.1 | 1 / 1 / 2 / 2 |
| github | 1,539 | 47% | 20% | 32% | 0% | 91.0 | 4 / 3 / 3 / 3 |
| apple | 2,351 | 40% | 19% | 9% | 60% | 28.1 | 3 / 4 / 4 / 4 |
| amazon | 1,155 | 41% | 17% | 2% | 0% | 8.7 | 5 / 5 / 5 / 5 |

Provider retention differences are small and partly persona mix; do not steer users between sign-in options on retention alone.

**What if hidden adopters added a work email?** 876 self-serve users at prospect companies are invisible today, mostly via apple, github sign-ins. If 30% added a work email, about 15 more companies would cross the sales trigger, on top of 156 visible today; with full visibility, 52 more would. A 'connect your work email to share with your team' prompt is a pipeline lever, not just an identity feature. *(Simulation on synthetic ground truth; real uptake must be measured with an A/B test of the prompt.)*

## Connected workspaces as identity evidence

Naive matching attributes 632 hidden users at 67% precision and creates 3 phantom sales-ready accounts. The worst naive error: 'Arworth Hiking Club' put 18 unrelated users into Arworth Retail. Guarded matching attributes 329 at 100% precision, recovers 34% of hidden employees, and adds 19 genuinely sales-ready accounts with 0 phantoms. Trust a workspace's verified domain; treat names as clues that need a colleague to corroborate them; drop guests and any workspace whose members already resolve to several companies. Synthetic data makes the guards look perfect; in production, audit a sample of attributions by hand each quarter.

| Matcher | Users attributed | Precision | Hidden employees recovered | Sales-ready accounts (correct / phantom) |
|---|---|---|---|---|
| Work email only | - | - | - | 156 / 0 |
| Naive connector match | 632 | 67% | 44% | 184 / 3 |
| Guarded connector match | 329 | 100% | 34% | 175 / 0 |

Naive errors by the guard that blocks them: community or side-project workspace: 182; guest in another company's workspace: 27. Workspace metadata is personal context: use it only in aggregate at the account level, within the permissions users granted, and never to contact an individual about a side project.

## Viral loops and reward policy

'Shared agent' grows the product most (3.26 activated recipients per 100 users; 56% of its sign-ups activate) and turns fastest. 'Shared asset (URL)' is the landing loop: it seeds the most new companies (51). 'Shared space / knowledge base' recipients retain best. Embeds and digests create many impressions but convert under 3% per share, and referral credits paid on sign-up bring sign-ups of which only 24% activate. In the reward simulation, paying per share sent nearly doubles shares but adds only +262 activated users. The stage-aware policy delivers the same pipeline as uniform weighted rewards (5.4 vs 5.4 extra prospects over the trigger; 3.7 vs 3.7 companies seeded by customers) while paying 1,335 rewards instead of 12,509. Uniform rewards buy more total sign-ups, mostly prosumer activity and colleagues who were already licensed.

![Viral loops](viral_loops.png)

Viral coefficients are single-generation. The reward simulation rests on stated behavioral assumptions (see ASSUMPTIONS in sangam/loops.py); test the policy with an A/B test, randomized by workspace, before rolling it out.

## Product-qualified accounts this week

Independent adopters at non-customers, scored with reasons. Signup spikes with low activation are suppressed as noise.

| Company | Score | Play | Why |
|---|---|---|---|
| Fenmont Holdings | 103 | Business development: offer a team pilot with admin controls | 14 independent users across 6 functions; 100% completed an agent action in week 0; 71% active in the last 4 weeks; 6 shared agents with colleagues; 4 on a paid plan |
| Torgate Retail | 103 | Route to existing cloud account team: propose an enterprise pilot | 34 independent users across 6 functions; 82% completed an agent action in week 0; 62% active in the last 4 weeks; 19 shared agents with colleagues; 4 on a paid plan |
| Verworth Holdings | 103 | Route to existing cloud account team: propose an enterprise pilot | 39 independent users across 6 functions; 87% completed an agent action in week 0; 54% active in the last 4 weeks; 23 shared agents with colleagues; 7 on a paid plan |
| Rosridge Retail | 102 | Route to existing cloud account team: propose an enterprise pilot | 37 independent users across 6 functions; 81% completed an agent action in week 0; 57% active in the last 4 weeks; 19 shared agents with colleagues; 5 on a paid plan |
| Arford Industries | 100 | Business development: offer a team pilot with admin controls | 31 independent users across 6 functions; 81% completed an agent action in week 0; 52% active in the last 4 weeks; 17 shared agents with colleagues; 7 on a paid plan |
| Jorholm Systems | 100 | Route to existing cloud account team: propose an enterprise pilot | 27 independent users across 6 functions; 74% completed an agent action in week 0; 59% active in the last 4 weeks; 16 shared agents with colleagues; 6 on a paid plan |
| Torgate Labs | 98 | Business development: offer a team pilot with admin controls | 34 independent users across 6 functions; 74% completed an agent action in week 0; 47% active in the last 4 weeks; 14 shared agents with colleagues; 10 on a paid plan |
| Salora Health | 97 | Route to existing cloud account team: propose an enterprise pilot | 21 independent users across 6 functions; 71% completed an agent action in week 0; 48% active in the last 4 weeks; 12 shared agents with colleagues; 5 on a paid plan |

## What would change these conclusions

- An onboarding experiment showing that nudging an agent action does *not* lift retention would mean the activation gap is intent, not cause.
- If identity resolution improves (fewer private-relay and personal addresses), account scores will shift; today about 4 in 10 self-serve users can be tied to a company.
- The sales trigger is fit on a few dozen historical contracts; several rules tie, so refit it as outcomes accumulate, and expect it to move by segment and company size.
- Thresholds (3+ functions, 60-point score, noise filter) are starting points to tune against real conversion outcomes.
