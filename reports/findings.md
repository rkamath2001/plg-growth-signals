# Findings memo: growth signals for an AI workspace product

*All data is synthetic, generated with a fixed seed. Effects were planted so every finding can be checked against a known answer.*

## Summary

Seven findings, each checked against planted ground truth (see `evals/`):

1. **Report external users separately.** Customer zero raises week-8 retention from 27% to 33%. Internal use is mandated, so it flatters every headline it touches.
2. **Activation is the first agent action.** External users who complete one in week 0 retain at 45% at week 8, versus 15% for question-only users (95% CI +29% to +31%), and the gap holds in every segment. This is observational; the next step is an onboarding experiment that nudges a first agent action.
3. **Breadth predicts retention.** Users linking 3+ connectors in week 0 retain at 49%, versus 19% for 1-2. Make the third connector a guided onboarding step.
4. **Don't credit the desktop app.** Its aggregate lift of +20% shrinks to +1% inside each segment. The internal rollout installed it by default.
5. **Test sales plays by account.** In simulation, randomizing accounts recovers the true lift (+3.9% vs +4.1%); splitting users inside a company reports +1.6%.
6. **Trigger sales on activated adopters, not sign-ups.** Companies with 5+ activated independent users across 2+ functions convert at 70%, 14.2x the 5% baseline.
7. **Rank channels by pipeline, not volume.** The top channel by sign-ups is not the top channel by sales-ready accounts; teammate invites lead on retention and pipeline.

## When to start an enterprise sales motion

Trigger an enterprise sales motion when a company has at least 5 activated independent users across 2+ functions. Those accounts convert at 70% versus a 5% baseline (14.2x), and the rule captures 56% of contracts while flagging 33 accounts. The best rule built on raw sign-up counts scores F1 0.47 against 0.62: sign-ups include event spikes that never activate.

![Sales trigger threshold](sales_trigger_threshold.png)

Counts only users resolvable to a company by email domain; private-relay and personal addresses are invisible, so the true number of adopters is higher. Re-fit the rule each quarter against new outcomes.

## Which acquisition channels matter

Rankings disagree. 'search' brings the most sign-ups, but 'teammate_invite' produces the most sales-ready accounts per 1,000 sign-ups (9.6) and retains 28% at week 8. 'webinar' and 'x' retain worst. Invest in invite loops and work-identity channels for pipeline; judge broad social channels on retained users, not sign-ups. Pipeline ranks for 'reddit', 'direct', 'youtube', 'webinar', 'x' rest on fewer than 5 accounts each; treat their order as noise.

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

*Attribution: first-touch at the account level; last-touch at the user level. Channels and intent are entangled: invited users arrive with a colleague's context. Test channel spend with geo or time holdouts before reallocating budget.*

## Product-qualified accounts this week

Independent adopters at non-customers, scored with reasons. Signup spikes with low activation are suppressed as noise.

| Company | Score | Play | Why |
|---|---|---|---|
| Salora Health | 98 | Route to existing cloud account team: propose an enterprise pilot | 20 independent users across 6 functions; 75% completed an agent action in week 0; 45% active in the last 4 weeks; 11 shared agents with colleagues; 5 on a paid plan |
| Ostwick Labs | 96 | Business development: offer a team pilot with admin controls | 22 independent users across 6 functions; 68% completed an agent action in week 0; 45% active in the last 4 weeks; 13 shared agents with colleagues; 6 on a paid plan |
| Torgate Labs | 94 | Business development: offer a team pilot with admin controls | 12 independent users across 5 functions; 83% completed an agent action in week 0; 58% active in the last 4 weeks; 7 shared agents with colleagues; 5 on a paid plan |
| Jorora Health | 94 | Business development: offer a team pilot with admin controls | 20 independent users across 6 functions; 65% completed an agent action in week 0; 40% active in the last 4 weeks; 9 shared agents with colleagues; 5 on a paid plan |
| Wilworth Group | 94 | Business development: offer a team pilot with admin controls | 22 independent users across 6 functions; 55% completed an agent action in week 0; 50% active in the last 4 weeks; 9 shared agents with colleagues; 8 on a paid plan |
| Beldale Industries | 93 | Business development: offer a team pilot with admin controls | 22 independent users across 6 functions; 64% completed an agent action in week 0; 36% active in the last 4 weeks; 10 shared agents with colleagues; 4 on a paid plan |
| Verworth Holdings | 93 | Route to existing cloud account team: propose an enterprise pilot | 19 independent users across 6 functions; 63% completed an agent action in week 0; 42% active in the last 4 weeks; 8 shared agents with colleagues; 5 on a paid plan |
| Verwick Holdings | 93 | Route to existing cloud account team: propose an enterprise pilot | 20 independent users across 5 functions; 60% completed an agent action in week 0; 40% active in the last 4 weeks; 7 shared agents with colleagues; 4 on a paid plan |

## What would change these conclusions

- An onboarding experiment showing that nudging an agent action does *not* lift retention would mean the activation gap is intent, not cause.
- If identity resolution improves (fewer private-relay and personal addresses), account scores will shift; today about 4 in 10 self-serve users can be tied to a company.
- The sales trigger is fit on about 40 historical contracts; refit it as outcomes accumulate, and expect it to move by segment and company size.
- Thresholds (3+ functions, 60-point score, noise filter) are starting points to tune against real conversion outcomes.
