"""Charts and the findings memo."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8d8b85"


def _style(ax, title, subtitle=None):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold", pad=22)
    if subtitle:
        ax.text(0, 1.03, subtitle, transform=ax.transAxes, fontsize=9, color=INK2)


def _fig():
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    return fig, ax


def retention_chart(curves: dict, path: Path):
    fig, ax = _fig()
    colors = [BLUE, ORANGE, AQUA, GRAY]
    styles = ["-", "-", "-", "--"]
    for (name, s), c, ls in zip(curves.items(), colors, styles):
        ax.plot(s.index, s.values, color=c, lw=2, ls=ls, marker="o", ms=4, label=name)
        ax.annotate(f"{name}  {s.iloc[-1]:.0%}", (s.index[-1], s.iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=8.5, color=INK)
    ax.set_xlim(0.7, 11.2)
    ax.set_xticks(range(1, 9))
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xlabel("Weeks after signup", color=INK2, fontsize=9)
    ax.set_ylabel("Share active", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, ncol=4,
              loc="upper left", bbox_to_anchor=(0, -0.13))
    _style(ax, "Activation is the first agent action, not the first question",
           "Weekly retention by week-0 behavior, external users; customer zero shown for contrast")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def simpson_chart(sim: dict, ds, path: Path):
    u = ds.users
    r = ds.activity.loc[u.user_id, 8].to_numpy()
    groups = ["All users", "Internal", "Enterprise (external)", "Self-serve"]
    masks = [np.ones(len(u), bool), (u.segment == "internal").to_numpy(),
             (u.segment == "enterprise_external").to_numpy(), (u.segment == "self_serve").to_numpy()]
    d = u.desktop.to_numpy()
    with_d = [np.nanmean(r[m & d]) for m in masks]
    without = [np.nanmean(r[m & ~d]) for m in masks]
    fig, ax = _fig()
    x = np.arange(len(groups))
    w = 0.36
    b1 = ax.bar(x - w / 2 - 0.01, with_d, w, color=BLUE, label="Desktop app installed")
    b2 = ax.bar(x + w / 2 + 0.01, without, w, color=ORANGE, label="Not installed")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015, f"{b.get_height():.0%}",
                    ha="center", fontsize=8.5, color=INK)
    ax.set_xticks(x, groups)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_ylabel("Week-8 retention", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2, loc="upper right")
    _style(ax, "The desktop app's 'lift' is a mix effect",
           f"Aggregate gap {sim['aggregate_lift']:+.0%}; inside each segment about {sim['weighted_within_lift']:+.0%}")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def experiment_chart(exp: dict, path: Path):
    fig, ax = _fig()
    bins = np.linspace(-0.08, 0.16, 37)
    for key, color, label in (("account", BLUE, "Randomize by account"),
                              ("user", ORANGE, "Randomize by user")):
        est = exp["estimates"][key]
        ax.hist(est, bins=bins, histtype="step", color=color, lw=2,
                label=f"{label} (mean {np.mean(est):+.1%})")
    ax.axvline(exp["true_effect"], color=INK, lw=1.5, ls="--")
    ax.text(exp["true_effect"], ax.get_ylim()[1] * 0.97, f"  true lift {exp['true_effect']:+.1%}",
            fontsize=8.5, color=INK, va="top")
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xlabel("Estimated lift from outreach (400 simulated tests)", color=INK2, fontsize=9)
    ax.set_ylabel("Tests", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2)
    _style(ax, "Test sales plays at the account level",
           "Colleagues share the outcome, so user-level splits leak treatment into the control group")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def threshold_chart(res: dict, path: Path):
    rows = res["conversion_by_activated_users"]
    labels = [r["activated_users"] for r in rows]
    rates = [r["conversion_rate"] for r in rows]
    ns = [r["accounts"] for r in rows]
    k = res["recommended_rule"]["min_activated"]
    fig, ax = _fig()
    lo = [int(l.split("-")[0].rstrip("+")) for l in labels]
    colors = [BLUE if v >= k else "#a9c9ee" for v in lo]
    bars = ax.bar(range(len(labels)), rates, 0.72, color=colors)
    for i, (b, n) in enumerate(zip(bars, ns)):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.03, f"{rates[i]:.0%}",
                ha="center", fontsize=8.5, color=INK, zorder=3,
                bbox=dict(fc=SURFACE, ec="none", pad=1))
        ax.text(b.get_x() + b.get_width() / 2, -0.07, f"n={n}", ha="center", fontsize=7.5, color=INK2)
    base = res["baseline_conversion"]
    ax.axhline(base, color=GRAY, lw=1.2, ls="--")
    ax.text(len(labels) - 0.55, base + 0.015, f"baseline {base:.0%}", ha="left", va="bottom", fontsize=8.5, color=INK2)
    cut = next(i for i, v in enumerate(lo) if v >= k)
    ax.axvline(cut - 0.5, color=INK, lw=1.2, ls=":")
    ax.text(cut - 0.55, 0.97, f"trigger: {k}+ activated users  ", fontsize=8.5,
            color=INK, va="top", ha="right")
    ax.set_xticks(range(len(labels)), labels)
    ax.set_xlim(-0.6, len(labels) + 0.4)
    ax.set_ylim(-0.1, 1.05)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xlabel("Activated independent users at the company (self-serve, resolved by email domain)",
                  color=INK2, fontsize=9)
    ax.set_ylabel("Signed an enterprise contract", color=INK2, fontsize=9)
    _style(ax, f"Start the sales motion at {k}+ activated users, not at a sign-up count",
           "Contract conversion by number of activated independent adopters; bars right of the line meet the trigger")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def findings_memo(r: dict, top, path: Path):
    inf, act, conn, sim, exp = (r["headline_inflation"], r["activation_test"], r["connector_breadth"],
                                r["simpson_check"], r["experiment"])
    c = {row["connectors_w0"]: row["w8_retention"] for row in conn["table"]}
    trig, chan = r["sales_trigger"], r["channel_ranking"]
    prov, wif = r["provider_ranking"], r["work_email_whatif"]
    con = r["connector_identity"]
    guards = "; ".join(f"{k}: {v}" for k, v in con["naive_errors_by_guard"].items())
    prov_rows = "\n".join(
        f"| {x['provider']} | {x['signups']:,} | {x['activation_rate']:.0%} | {x['w8_retention']:.0%} | "
        f"{x['company_resolved']:.0%} | {x['private_relay']:.0%} | {x['ready_users_per_1k']} | "
        f"{x['by_volume']} / {x['by_retention']} / {x['by_visibility']} / {x['by_pipeline']} |"
        for x in prov["table"])
    chan_rows = "\n".join(
        f"| {x['source']} | {x['signups']:,} | {x['activation_rate']:.0%} | {x['w8_retention']:.0%} | "
        f"{x['company_resolved']:.0%} | {x['ready_per_1k']} | {x['by_volume']} / {x['by_retention']} / {x['by_pipeline']} |"
        for x in chan["table"])
    rows = "\n".join(
        f"| {t.company} | {t.score:.0f} | {t.play} | {t.reasons} |"
        for t in top.itertuples())
    md = f"""# Findings memo: growth signals for an AI workspace product

*All data is synthetic, generated with a fixed seed. The data was generated to enable the cohort analysis and prove the methodology; every finding is checked against the expected result.*

## Summary

Ten findings, each checked against the expected result (see `evals/`):

1. **Report external users separately.** Customer zero raises week-8 retention from {inf['w8_retention_external_only']:.0%} to {inf['w8_retention_all_users']:.0%}. Internal use is mandated, so it flatters every headline it touches.
2. **Activation is the first agent action.** External users who complete one in week 0 retain at {act['cohorts']['agent_action']['w8_retention']:.0%} at week 8, versus {act['cohorts']['question_only']['w8_retention']:.0%} for question-only users (95% CI {act['ci95'][0]:+.0%} to {act['ci95'][1]:+.0%}), and the gap holds in every segment. This is observational; the next step is an onboarding experiment that nudges a first agent action.
3. **Breadth predicts retention.** Users linking 3+ connectors in week 0 retain at {c['3+']:.0%}, versus {c['1-2']:.0%} for 1-2. Make the third connector a guided onboarding step.
4. **Don't credit the desktop app.** Its aggregate lift of {sim['aggregate_lift']:+.0%} shrinks to {sim['weighted_within_lift']:+.0%} inside each segment. The internal rollout installed it by default.
5. **Test sales plays by account.** In simulation, randomizing accounts recovers the true lift ({exp['account_level_estimate']['mean']:+.1%} vs {exp['true_effect']:+.1%}); splitting users inside a company reports {exp['user_level_estimate']['mean']:+.1%}.
6. **Trigger sales on activated adopters, not sign-ups.** Companies with {trig['recommended_rule']['min_activated']}+ activated independent users convert at {trig['recommended_rule']['precision']:.0%}, {trig['lift_over_baseline']}x the {trig['baseline_conversion']:.0%} baseline.
7. **Rank channels by pipeline, not volume.** The top channel by sign-ups is not the top channel by sales-ready accounts; teammate invites lead on retention and pipeline.
8. **Sign-in provider decides visibility.** Google and work-email sign-ups reveal the company about half the time; Apple and Amazon almost never. A work-email prompt at the moment of sharing would put more companies over the sales trigger.
9. **Connected workspaces reveal employers, if guarded.** Matching Slack, Teams and Jira workspaces naively invents adopters from school clubs, side projects and client workspaces; trusting verified domains and requiring corroboration for names recovers real sales-ready accounts with no phantoms.
10. **Agent shares grow, asset shares land; reward activation, by account stage.** Paying per share sent buys shares, not users; a stage-aware policy paid on the recipient's first agent action keeps the pipeline gains at a fraction of the cost.

## When to start an enterprise sales motion

{trig['finding']}

![Sales trigger threshold](sales_trigger_threshold.png)

{trig['caveat']}

## Which acquisition channels matter

{chan['finding']}

| Channel | Sign-ups | Activation | Week-8 retention | Resolved to a company | Sales-ready accounts per 1,000 | Rank: volume / retention / pipeline |
|---|---|---|---|---|---|---|
{chan_rows}

*Attribution: {chan['attribution']}. {chan['caveat']}*

## Sign-in providers: who can we see?

{prov['finding']}

| Provider | Sign-ups | Activation | Week-8 retention | Resolved to a company | Private relay | Users at sales-ready accounts per 1,000 | Rank: volume / retention / visibility / pipeline |
|---|---|---|---|---|---|---|---|
{prov_rows}

{prov['caveat']}

**What if hidden adopters added a work email?** {wif['finding']} *({wif['method']})*

## Connected workspaces as identity evidence

{con['finding']}

| Matcher | Users attributed | Precision | Hidden employees recovered | Sales-ready accounts (correct / phantom) |
|---|---|---|---|---|
| Work email only | - | - | - | {con['email_only']['correct_ready']} / {con['email_only']['phantom_ready']} |
| Naive connector match | {con['naive']['users_attributed']} | {con['naive']['precision']:.0%} | {con['naive']['recall_of_hidden']:.0%} | {con['naive']['correct_ready']} / {con['naive']['phantom_ready']} |
| Guarded connector match | {con['guarded']['users_attributed']} | {con['guarded']['precision']:.0%} | {con['guarded']['recall_of_hidden']:.0%} | {con['guarded']['correct_ready']} / {con['guarded']['phantom_ready']} |

Naive errors by the guard that blocks them: {guards}. {con['caveat']}

## Viral loops and reward policy

{r['viral_loops']['finding']}

![Viral loops](viral_loops.png)

{r['viral_loops']['caveat']}

## Product-qualified accounts this week

Independent adopters at non-customers, scored with reasons. Signup spikes with low activation are suppressed as noise.

| Company | Score | Play | Why |
|---|---|---|---|
{rows}

## What would change these conclusions

- An onboarding experiment showing that nudging an agent action does *not* lift retention would mean the activation gap is intent, not cause.
- If identity resolution improves (fewer private-relay and personal addresses), account scores will shift; today about 4 in 10 self-serve users can be tied to a company.
- The sales trigger is fit on a few dozen historical contracts; several rules tie, so refit it as outcomes accumulate, and expect it to move by segment and company size.
- Thresholds (3+ functions, 60-point score, noise filter) are starting points to tune against real conversion outcomes.
"""
    path.write_text(md, encoding="utf-8")


def write_json(results: dict, path: Path):
    slim = {k: {kk: vv for kk, vv in v.items() if kk != "estimates"} for k, v in results.items()}
    path.write_text(json.dumps(slim, indent=2, default=str), encoding="utf-8")


def loops_chart(loops: dict, path: Path):
    """Activated recipients per 100 users vs cycle time, one labeled point per loop."""
    from .loops import LOOP_LABEL
    sc = loops["scorecard"]
    fig, ax = _fig()
    offsets = {"embed": (-12, 40), "digest": (12, -2), "agent": (12, 14), "asset": (12, 16)}
    for r in sc:
        x, y = r["median_cycle_days"], r["k_activated_per_100"]
        size = 40 + r["shares"] / 120
        ax.scatter(x, y, s=size, color=BLUE, alpha=0.85, edgecolor=SURFACE, linewidth=2, zorder=3)
        dx, dy = offsets.get(r["loop"], (12, 4))
        ax.annotate(f"{LOOP_LABEL[r['loop']]}\n{r['activation_of_signups']:.0%} of sign-ups activate",
                    (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8.5, color=INK,
                    va="center", ha="right" if dx < 0 else "left")
    ax.set_xscale("log")
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xticks([1, 2, 4, 8, 16, 32], ["1", "2", "4", "8", "16", "32"])
    ax.set_xlim(1.2, 60)
    ax.set_ylim(0, max(r["k_activated_per_100"] for r in sc) * 1.25)
    ax.set_xlabel("Median days from share to sign-up (log scale)", color=INK2, fontsize=9)
    ax.set_ylabel("Activated recipients per 100 users", color=INK2, fontsize=9)
    _style(ax, "Agent shares grow fastest; embeds and digests barely convert",
           "Viral coefficient on activated recipients vs cycle time; dot size = shares sent")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
