# Findings memo: growth signals for an AI workspace product

*All data is synthetic, generated with a fixed seed. Effects were planted so every finding can be checked against a known answer.*

## Summary

Ten findings, each checked against planted ground truth (see `evals/`):

1. **Report external users separately.** Customer zero raises week-8 retention from 27% to 33%. Internal use is mandated, so it flatters every headline it touches.
2. **Activation is the first agent action.** External users who complete one in week 0 retain at 45% at week 8, versus 15% for question-only users (95% CI +29% to +31%), and the gap holds in every segment. This is observational; the next step is an onboarding experiment that nudges a first agent action.
3. **Breadth predicts retention.** Users linking 3+ connectors in week 0 retain at 49%, versus 19% for 1-2. Make the third connector a guided onboarding step.
4. **Don't credit the desktop app.** Its aggregate lift of +18% shrinks to -1% inside each segment. The internal rollout installed it by default.
5. **Test sales plays by account.** In simulation, randomizing accounts recovers the true lift (+3.9% vs +4.0%); splitting users inside a company reports +1.8%.
6. **Trigger sales on activated adopters, not sign-ups.** Companies with 5+ activated independent users convert at 50%, 3.4x the 15% baseline.
7. **Rank channels by pipeline, not volume.** The top channel by sign-ups is not the top channel by sales-ready accounts; teammate invites lead on retention and pipeline.
8. **Sign-in provider decides visibility.** Google and work-email sign-ups reveal the company about half the time; Apple and Amazon almost never. A work-email prompt at the moment of sharing would put more companies over the sales trigger.
9. **Connected workspaces reveal employers, if guarded.** Matching Slack, Teams and Jira workspaces naively invents adopters from school clubs, side projects and client workspaces; trusting verified domains and requiring corroboration for names recovers real sales-ready accounts with no phantoms.
10. **Agent shares grow, asset shares land; reward activation, by account stage.** Paying per share sent buys shares, not users; a stage-aware policy paid on the recipient's first agent action keeps the pipeline gains at a fraction of the cost.

## When to start an enterprise sales motion

Start an enterprise sales motion at 5+ activated independent users. Those companies convert at 50% versus a 15% baseline (3.4x); the rule captures 59% of contracts while flagging 145 accounts. At 4 activated users conversion is 24%: run champion enablement there, not sales. Requiring a minimum number of functions did not beat the simple count within noise. The best sign-up-count rule scores F1 0.42 against 0.55, because sign-ups include event spikes that never activate.

![Sales trigger threshold](sales_trigger_threshold.png)

Fit on 123 contracts: 6 rules are statistically tied, so the simplest was chosen. Counts only users resolvable to a company by email domain, so the true number of adopters is higher. Refit each quarter and by segment as outcomes accumulate.

## Which acquisition channels matter

Rankings disagree. 'search' brings the most sign-ups, but 'teammate_invite' produces the most sales-ready accounts per 1,000 sign-ups (28.8) and retains 28% at week 8. 'webinar' and 'reddit' retain worst. Invest in invite loops and work-identity channels for pipeline; judge broad social channels on retained users, not sign-ups. Pipeline ranks for 'webinar' rest on fewer than 5 accounts; treat that rank as noise.

| Channel | Sign-ups | Activation | Week-8 retention | Resolved to a company | Sales-ready accounts per 1,000 | Rank: volume / retention / pipeline |
|---|---|---|---|---|---|---|
| teammate_invite | 1,147 | 54% | 28% | 63% | 28.8 | 7 / 1 / 1 |
| linkedin | 1,386 | 46% | 23% | 61% | 26.7 | 2 / 2 / 2 |
| direct | 1,149 | 42% | 20% | 37% | 15.7 | 6 / 3 / 3 |
| search | 1,970 | 42% | 19% | 36% | 10.2 | 1 / 4 / 4 |
| reddit | 1,288 | 32% | 14% | 15% | 8.5 | 4 / 7 / 5 |
| x | 1,311 | 34% | 16% | 19% | 7.6 | 3 / 6 / 6 |
| webinar | 277 | 12% | 0% | 87% | 7.2 | 8 / 8 / 7 |
| youtube | 1,227 | 40% | 17% | 24% | 4.9 | 5 / 5 / 8 |

*Attribution: first-touch at the account level; last-touch at the user level. Channels and intent are entangled: invited users arrive with a colleague's context. Test channel spend with geo or time holdouts before reallocating budget.*

## Sign-in providers: who can we see?

Provider decides visibility more than quality. 50% of Google and 58% of email sign-ups can be tied to a company, versus 4% for 'amazon' and 9% for 'apple'. 'microsoft' users retain best (23%), consistent with a builder persona. The pipeline ranking mostly mirrors visibility: an account you cannot see never reaches the sales trigger.

| Provider | Sign-ups | Activation | Week-8 retention | Resolved to a company | Private relay | Users at sales-ready accounts per 1,000 | Rank: volume / retention / visibility / pipeline |
|---|---|---|---|---|---|---|---|
| microsoft | 1,392 | 46% | 23% | 61% | 0% | 177.4 | 5 / 1 / 1 / 1 |
| email | 2,674 | 43% | 19% | 58% | 0% | 163.1 | 2 / 5 / 2 / 2 |
| google | 6,149 | 46% | 21% | 50% | 0% | 144.7 | 1 / 3 / 3 / 3 |
| github | 1,581 | 48% | 22% | 30% | 0% | 89.8 | 4 / 2 / 4 / 4 |
| apple | 2,156 | 41% | 19% | 9% | 59% | 25.5 | 3 / 4 / 5 / 5 |
| amazon | 1,045 | 37% | 18% | 4% | 0% | 9.6 | 6 / 6 / 6 / 6 |

Provider retention differences are small and partly persona mix; do not steer users between sign-in options on retention alone.

**What if hidden adopters added a work email?** 1015 self-serve users at prospect companies are invisible today, mostly via apple, github sign-ins. If 30% added a work email, about 18 more companies would cross the sales trigger, on top of 145 visible today; with full visibility, 62 more would. A 'connect your work email to share with your team' prompt is a pipeline lever, not just an identity feature. *(Simulation on synthetic ground truth; real uptake must be measured with an A/B test of the prompt.)*

## Connected workspaces as identity evidence

Naive matching attributes 701 hidden users at 70% precision and creates 9 phantom sales-ready accounts. The worst naive error: 'Lumora Makers' put 16 unrelated users into Lumora Retail. Guarded matching attributes 374 at 100% precision, recovers 34% of hidden employees, and adds 18 genuinely sales-ready accounts with 0 phantoms. Trust a workspace's verified domain; treat names as clues that need a colleague to corroborate them; drop guests and any workspace whose members already resolve to several companies. Synthetic data makes the guards look perfect; in production, audit a sample of attributions by hand each quarter.

| Matcher | Users attributed | Precision | Hidden employees recovered | Sales-ready accounts (correct / phantom) |
|---|---|---|---|---|
| Work email only | - | - | - | 145 / 0 |
| Naive connector match | 701 | 70% | 45% | 168 / 9 |
| Guarded connector match | 374 | 100% | 34% | 163 / 0 |

Naive errors by the guard that blocks them: community or side-project workspace: 193; guest in another company's workspace: 18. Workspace metadata is personal context: use it only in aggregate at the account level, within the permissions users granted, and never to contact an individual about a side project.

## Viral loops and reward policy

'Shared agent' grows the product most (3.25 activated recipients per 100 users; 56% of its sign-ups activate) and turns fastest. 'Shared asset (URL)' is the landing loop: it seeds the most new companies (49). 'Shared space / knowledge base' recipients retain best. Embeds and digests create many impressions but convert under 3% per share, and referral credits paid on sign-up bring sign-ups of which only 31% activate. In the reward simulation, paying per share sent nearly doubles shares but adds only +269 activated users. The stage-aware policy delivers the same pipeline as uniform weighted rewards (7.3 vs 7.3 extra prospects over the trigger; 3.4 vs 3.4 companies seeded by customers) while paying 1,340 rewards instead of 12,488. Uniform rewards buy more total sign-ups, mostly prosumer activity and colleagues who were already licensed.

![Viral loops](viral_loops.png)

Viral coefficients are single-generation. The reward simulation rests on stated behavioral assumptions (see BEHAVIOR in sangam/policy.py); test the policy with an A/B test, randomized by workspace, before rolling it out.

## Product-qualified accounts this week

Independent adopters at non-customers, scored with reasons. Signup spikes with low activation are suppressed as noise.

| Company | Score | Play | Why |
|---|---|---|---|
| Arford Industries | 102 | Business development: offer a team pilot with admin controls | 19 independent users across 6 functions; 84% completed an agent action in week 0; 58% active in the last 4 weeks; 8 shared agents with colleagues; 5 on a paid plan |
| Verworth Holdings | 100 | Route to existing cloud account team: propose an enterprise pilot | 34 independent users across 6 functions; 76% completed an agent action in week 0; 56% active in the last 4 weeks; 20 shared agents with colleagues; 5 on a paid plan |
| Yaria Holdings | 99 | Business development: offer a team pilot with admin controls | 27 independent users across 6 functions; 74% completed an agent action in week 0; 52% active in the last 4 weeks; 14 shared agents with colleagues; 4 on a paid plan |
| Fenmont Holdings | 98 | Business development: offer a team pilot with admin controls | 30 independent users across 6 functions; 67% completed an agent action in week 0; 57% active in the last 4 weeks; 14 shared agents with colleagues; 4 on a paid plan |
| Torford Media | 98 | Business development: offer a team pilot with admin controls | 44 independent users across 6 functions; 68% completed an agent action in week 0; 55% active in the last 4 weeks; 29 shared agents with colleagues; 5 on a paid plan |
| Beldale Industries | 98 | Business development: offer a team pilot with admin controls | 20 independent users across 6 functions; 70% completed an agent action in week 0; 50% active in the last 4 weeks; 11 shared agents with colleagues; 5 on a paid plan |
| Fenport Media | 97 | Route to existing cloud account team: propose an enterprise pilot | 32 independent users across 6 functions; 69% completed an agent action in week 0; 50% active in the last 4 weeks; 15 shared agents with colleagues; 7 on a paid plan |
| Jorora Health | 97 | Business development: offer a team pilot with admin controls | 38 independent users across 6 functions; 68% completed an agent action in week 0; 47% active in the last 4 weeks; 19 shared agents with colleagues; 7 on a paid plan |

## What would change these conclusions

- An onboarding experiment showing that nudging an agent action does *not* lift retention would mean the activation gap is intent, not cause.
- If identity resolution improves (fewer private-relay and personal addresses), account scores will shift; today about 4 in 10 self-serve users can be tied to a company.
- The sales trigger is fit on a few dozen historical contracts; several rules tie, so refit it as outcomes accumulate, and expect it to move by segment and company size.
- Thresholds (3+ functions, 60-point score, noise filter) are starting points to tune against real conversion outcomes.
