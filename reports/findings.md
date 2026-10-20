# Findings memo: growth signals for an AI workspace product

*All data is synthetic, generated with a fixed seed. Effects were planted so every finding can be checked against a known answer.*

## Summary

Ten findings, each checked against planted ground truth (see `evals/`):

1. **Report external users separately.** Customer zero raises week-8 retention from 26% to 34%. Internal use is mandated, so it flatters every headline it touches.
2. **Activation is the first agent action.** External users who complete one in week 0 retain at 43% at week 8, versus 14% for question-only users (95% CI +28% to +31%), and the gap holds in every segment. This is observational; the next step is an onboarding experiment that nudges a first agent action.
3. **Breadth predicts retention.** Users linking 3+ connectors in week 0 retain at 48%, versus 19% for 1-2. Make the third connector a guided onboarding step.
4. **Don't credit the desktop app.** Its aggregate lift of +23% shrinks to +0% inside each segment. The internal rollout installed it by default.
5. **Test sales plays by account.** In simulation, randomizing accounts recovers the true lift (+4.0% vs +4.0%); splitting users inside a company reports +1.7%.
6. **Trigger sales on activated adopters, not sign-ups.** Companies with 5+ activated independent users convert at 57%, 2.8x the 20% baseline.
7. **Rank channels by pipeline, not volume.** The top channel by sign-ups is not the top channel by sales-ready accounts; teammate invites lead on retention and pipeline.
8. **Sign-in provider decides visibility.** Google and work-email sign-ups reveal the company about half the time; Apple and Amazon almost never. A work-email prompt at the moment of sharing would put more companies over the sales trigger.
9. **Connected workspaces reveal employers, if guarded.** Matching Slack, Teams and Jira workspaces naively invents adopters from school clubs, side projects and client workspaces; trusting verified domains and requiring corroboration for names recovers real sales-ready accounts with no phantoms.
10. **Agent shares grow, asset shares land; reward activation, by account stage.** Paying per share sent buys shares, not users; a stage-aware policy paid on the recipient's first agent action keeps the pipeline gains at a fraction of the cost.

## When to start an enterprise sales motion

Start an enterprise sales motion at 5+ activated independent users. Those companies convert at 57% versus a 20% baseline (2.8x); the rule captures 61% of contracts while flagging 180 accounts. At 4 activated users conversion is 27%: run champion enablement there, not sales. Requiring a minimum number of functions did not beat the simple count within noise. The best sign-up-count rule scores F1 0.50 against 0.59, because sign-ups include event spikes that never activate.

![Sales trigger threshold](sales_trigger_threshold.png)

Fit on 170 contracts: 6 rules are statistically tied, so the simplest was chosen. Counts only users resolvable to a company by email domain, so the true number of adopters is higher. Refit each quarter and by segment as outcomes accumulate.

## Which acquisition channels matter

Rankings disagree. 'search' brings the most sign-ups, but 'teammate_invite' produces the most sales-ready accounts per 1,000 sign-ups (25.2) and retains 25% at week 8. 'webinar' and 'reddit' retain worst. Invest in invite loops and work-identity channels for pipeline; judge broad social channels on retained users, not sign-ups. Pipeline ranks for 'webinar', 'reddit' rest on fewer than 5 accounts each; treat their order as noise.

| Channel | Sign-ups | Activation | Week-8 retention | Resolved to a company | Sales-ready accounts per 1,000 | Rank: volume / retention / pipeline |
|---|---|---|---|---|---|---|
| teammate_invite | 1,630 | 55% | 25% | 62% | 25.2 | 6 / 1 / 1 |
| linkedin | 1,949 | 47% | 22% | 59% | 15.4 | 2 / 2 / 2 |
| search | 2,807 | 41% | 20% | 35% | 15.0 | 1 / 3 / 3 |
| direct | 1,630 | 39% | 18% | 34% | 10.4 | 6 / 4 / 4 |
| webinar | 304 | 10% | 1% | 88% | 9.9 | 8 / 8 / 5 |
| x | 1,840 | 32% | 15% | 20% | 8.2 | 3 / 6 / 6 |
| youtube | 1,829 | 36% | 17% | 26% | 7.7 | 4 / 5 / 7 |
| reddit | 1,813 | 31% | 13% | 14% | 2.2 | 5 / 7 / 8 |

*Attribution: first-touch at the account level; last-touch at the user level. Channels and intent are entangled: invited users arrive with a colleague's context. Test channel spend with geo or time holdouts before reallocating budget.*

## Sign-in providers: who can we see?

Provider decides visibility more than quality. 49% of Google and 55% of email sign-ups can be tied to a company, versus 4% for 'amazon' and 7% for 'apple'. 'github' users retain best (24%), consistent with a builder persona. The pipeline ranking mostly mirrors visibility: an account you cannot see never reaches the sales trigger.

| Provider | Sign-ups | Activation | Week-8 retention | Resolved to a company | Private relay | Users at sales-ready accounts per 1,000 | Rank: volume / retention / visibility / pipeline |
|---|---|---|---|---|---|---|---|
| microsoft | 1,630 | 40% | 18% | 58% | 0% | 189.6 | 5 / 5 / 1 / 1 |
| email | 3,165 | 43% | 20% | 55% | 0% | 160.8 | 2 / 3 / 2 / 2 |
| google | 7,468 | 44% | 21% | 49% | 0% | 154.9 | 1 / 2 / 3 / 3 |
| github | 1,925 | 46% | 24% | 27% | 0% | 80.0 | 4 / 1 / 4 / 4 |
| apple | 2,734 | 40% | 19% | 7% | 61% | 19.8 | 3 / 4 / 5 / 5 |
| amazon | 1,412 | 37% | 16% | 4% | 0% | 9.2 | 6 / 6 / 6 / 6 |

Provider retention differences are small and partly persona mix; do not steer users between sign-in options on retention alone.

**What if hidden adopters added a work email?** 1034 self-serve users at prospect companies are invisible today, mostly via github, apple sign-ins. If 30% added a work email, about 25 more companies would cross the sales trigger, on top of 180 visible today; with full visibility, 86 more would. A 'connect your work email to share with your team' prompt is a pipeline lever, not just an identity feature. *(Simulation on synthetic ground truth; real uptake must be measured with an A/B test of the prompt.)*

## Connected workspaces as identity evidence

Naive matching attributes 790 hidden users at 72% precision and creates 9 phantom sales-ready accounts. The worst naive error: 'Lumora Book Club' put 19 unrelated users into Lumora Retail. Guarded matching attributes 454 at 100% precision, recovers 38% of hidden employees, and adds 37 genuinely sales-ready accounts with 0 phantoms. Trust a workspace's verified domain; treat names as clues that need a colleague to corroborate them; drop guests and any workspace whose members already resolve to several companies. Synthetic data makes the guards look perfect; in production, audit a sample of attributions by hand each quarter.

| Matcher | Users attributed | Precision | Hidden employees recovered | Sales-ready accounts (correct / phantom) |
|---|---|---|---|---|
| Work email only | - | - | - | 180 / 0 |
| Naive connector match | 790 | 72% | 48% | 223 / 9 |
| Guarded connector match | 454 | 100% | 38% | 217 / 0 |

Naive errors by the guard that blocks them: community or side-project workspace: 199; guest in another company's workspace: 25. Workspace metadata is personal context: use it only in aggregate at the account level, within the permissions users granted, and never to contact an individual about a side project.

## Viral loops and reward policy

'Shared agent' grows the product most (2.7 activated recipients per 100 users; 56% of its sign-ups activate) and turns fastest. 'Shared asset (URL)' is the landing loop: it seeds the most new companies (60). 'Shared space / knowledge base' recipients retain best. Embeds and digests create many impressions but convert under 3% per share, and referral credits paid on sign-up bring sign-ups of which only 31% activate. In the reward simulation, paying per share sent nearly doubles shares but adds only +233 activated users. The stage-aware policy delivers the same pipeline as uniform weighted rewards (5.5 vs 5.5 extra prospects over the trigger; 2.4 vs 2.4 companies seeded by customers) while paying 1,039 rewards instead of 12,276. Uniform rewards buy more total sign-ups, mostly prosumer activity and colleagues who were already licensed.

![Viral loops](viral_loops.png)

Viral coefficients are single-generation. The reward simulation rests on stated behavioral assumptions (see BEHAVIOR in sangam/policy.py); test the policy with an A/B test, randomized by workspace, before rolling it out.

## Product-qualified accounts this week

Independent adopters at non-customers, scored with reasons. Signup spikes with low activation are suppressed as noise.

| Company | Score | Play | Why |
|---|---|---|---|
| Verworth Holdings | 104 | Route to existing cloud account team: propose an enterprise pilot | 30 independent users across 6 functions; 87% completed an agent action in week 0; 63% active in the last 4 weeks; 16 shared agents with colleagues; 4 on a paid plan |
| Torgate Retail | 104 | Route to existing cloud account team: propose an enterprise pilot | 27 independent users across 6 functions; 70% completed an agent action in week 0; 81% active in the last 4 weeks; 17 shared agents with colleagues; 5 on a paid plan |
| Ulia Financial | 103 | Business development: offer a team pilot with admin controls | 16 independent users across 6 functions; 81% completed an agent action in week 0; 88% active in the last 4 weeks; 7 shared agents with colleagues; 3 on a paid plan |
| Fenport Media | 102 | Route to existing cloud account team: propose an enterprise pilot | 26 independent users across 6 functions; 65% completed an agent action in week 0; 81% active in the last 4 weeks; 12 shared agents with colleagues; 3 on a paid plan |
| Quinworth Works | 100 | Business development: offer a team pilot with admin controls | 23 independent users across 6 functions; 65% completed an agent action in week 0; 70% active in the last 4 weeks; 11 shared agents with colleagues; 4 on a paid plan |
| Ulford Partners | 100 | Route to existing cloud account team: propose an enterprise pilot | 20 independent users across 5 functions; 70% completed an agent action in week 0; 65% active in the last 4 weeks; 8 shared agents with colleagues; 3 on a paid plan |
| Wilworth Group | 99 | Business development: offer a team pilot with admin controls | 29 independent users across 6 functions; 76% completed an agent action in week 0; 52% active in the last 4 weeks; 12 shared agents with colleagues; 4 on a paid plan |
| Ulholm Holdings | 99 | Business development: offer a team pilot with admin controls | 23 independent users across 6 functions; 74% completed an agent action in week 0; 52% active in the last 4 weeks; 14 shared agents with colleagues; 4 on a paid plan |

## What would change these conclusions

- An onboarding experiment showing that nudging an agent action does *not* lift retention would mean the activation gap is intent, not cause.
- If identity resolution improves (fewer private-relay and personal addresses), account scores will shift; today about 4 in 10 self-serve users can be tied to a company.
- The sales trigger is fit on a few dozen historical contracts; several rules tie, so refit it as outcomes accumulate, and expect it to move by segment and company size.
- Thresholds (3+ functions, 60-point score, noise filter) are starting points to tune against real conversion outcomes.
