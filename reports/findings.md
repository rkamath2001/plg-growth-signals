# Findings memo: growth signals for an AI workspace product

*All data is synthetic, generated with a fixed seed. Effects were planted so every finding can be checked against a known answer.*

## Summary

Five findings, each checked against planted ground truth (see `evals/`):

1. **Report external users separately.** Customer zero raises week-8 retention from 27% to 33%. Internal use is mandated, so it flatters every headline it touches.
2. **Activation is the first agent action.** External users who complete one in week 0 retain at 45% at week 8, versus 15% for question-only users (95% CI +29% to +32%), and the gap holds in every segment. This is observational; the next step is an onboarding experiment that nudges a first agent action.
3. **Breadth predicts retention.** Users linking 3+ connectors in week 0 retain at 49%, versus 19% for 1-2. Make the third connector a guided onboarding step.
4. **Don't credit the desktop app.** Its aggregate lift of +20% shrinks to +0% inside each segment. The internal rollout installed it by default.
5. **Test sales plays by account.** In simulation, randomizing accounts recovers the true lift (+4.1% vs +4.0%); splitting users inside a company reports +1.5%.

## Product-qualified accounts this week

Independent adopters at non-customers, scored with reasons. Signup spikes with low activation are suppressed as noise.

| Company | Score | Play | Why |
|---|---|---|---|
| Ulnex Holdings | 93 | Business development: offer a team pilot with admin controls | 21 independent users across 6 functions; 67% completed an agent action in week 0; 33% active in the last 4 weeks; 7 shared agents with colleagues; 6 on a paid plan |
| Gargate Group | 91 | Business development: offer a team pilot with admin controls | 20 independent users across 6 functions; 65% completed an agent action in week 0; 25% active in the last 4 weeks; 7 shared agents with colleagues; 8 on a paid plan |
| Wilmont Industries | 91 | Business development: offer a team pilot with admin controls | 19 independent users across 6 functions; 53% completed an agent action in week 0; 42% active in the last 4 weeks; 4 shared agents with colleagues; 5 on a paid plan |
| Rosridge Retail | 90 | Route to existing cloud account team: propose an enterprise pilot | 15 independent users across 6 functions; 67% completed an agent action in week 0; 40% active in the last 4 weeks; 5 shared agents with colleagues; 6 on a paid plan |
| Beldale Industries | 89 | Business development: offer a team pilot with admin controls | 19 independent users across 6 functions; 58% completed an agent action in week 0; 47% active in the last 4 weeks; 8 shared agents with colleagues; 2 on a paid plan |
| Yaria Holdings | 89 | Business development: offer a team pilot with admin controls | 13 independent users across 5 functions; 77% completed an agent action in week 0; 38% active in the last 4 weeks; 5 shared agents with colleagues; 3 on a paid plan |
| Ulholm Holdings | 88 | Business development: offer a team pilot with admin controls | 8 independent users across 5 functions; 88% completed an agent action in week 0; 62% active in the last 4 weeks; 6 shared agents with colleagues; 2 on a paid plan |
| Verworth Holdings | 88 | Route to existing cloud account team: propose an enterprise pilot | 22 independent users across 6 functions; 59% completed an agent action in week 0; 18% active in the last 4 weeks; 5 shared agents with colleagues; 8 on a paid plan |

## What would change these conclusions

- An onboarding experiment showing that nudging an agent action does *not* lift retention would mean the activation gap is intent, not cause.
- If identity resolution improves (fewer private-relay and personal addresses), account scores will shift; today about 4 in 10 self-serve users can be tied to a company.
- Thresholds (3+ functions, 60-point score, noise filter) are starting points to tune against real conversion outcomes.
