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


def findings_memo(r: dict, top, path: Path):
    inf, act, conn, sim, exp = (r["headline_inflation"], r["activation_test"], r["connector_breadth"],
                                r["simpson_check"], r["experiment"])
    c = {row["connectors_w0"]: row["w8_retention"] for row in conn["table"]}
    rows = "\n".join(
        f"| {t.company} | {t.score:.0f} | {t.play} | {t.reasons} |"
        for t in top.itertuples())
    md = f"""# Findings memo: growth signals for an AI workspace product

*All data is synthetic, generated with a fixed seed. Effects were planted so every finding can be checked against a known answer.*

## Summary

Five findings, each checked against planted ground truth (see `evals/`):

1. **Report external users separately.** Customer zero raises week-8 retention from {inf['w8_retention_external_only']:.0%} to {inf['w8_retention_all_users']:.0%}. Internal use is mandated, so it flatters every headline it touches.
2. **Activation is the first agent action.** External users who complete one in week 0 retain at {act['cohorts']['agent_action']['w8_retention']:.0%} at week 8, versus {act['cohorts']['question_only']['w8_retention']:.0%} for question-only users (95% CI {act['ci95'][0]:+.0%} to {act['ci95'][1]:+.0%}), and the gap holds in every segment. This is observational; the next step is an onboarding experiment that nudges a first agent action.
3. **Breadth predicts retention.** Users linking 3+ connectors in week 0 retain at {c['3+']:.0%}, versus {c['1-2']:.0%} for 1-2. Make the third connector a guided onboarding step.
4. **Don't credit the desktop app.** Its aggregate lift of {sim['aggregate_lift']:+.0%} shrinks to {sim['weighted_within_lift']:+.0%} inside each segment. The internal rollout installed it by default.
5. **Test sales plays by account.** In simulation, randomizing accounts recovers the true lift ({exp['account_level_estimate']['mean']:+.1%} vs {exp['true_effect']:+.1%}); splitting users inside a company reports {exp['user_level_estimate']['mean']:+.1%}.

## Product-qualified accounts this week

Independent adopters at non-customers, scored with reasons. Signup spikes with low activation are suppressed as noise.

| Company | Score | Play | Why |
|---|---|---|---|
{rows}

## What would change these conclusions

- An onboarding experiment showing that nudging an agent action does *not* lift retention would mean the activation gap is intent, not cause.
- If identity resolution improves (fewer private-relay and personal addresses), account scores will shift; today about 4 in 10 self-serve users can be tied to a company.
- Thresholds (3+ functions, 60-point score, noise filter) are starting points to tune against real conversion outcomes.
"""
    path.write_text(md)


def write_json(results: dict, path: Path):
    slim = {k: {kk: vv for kk, vv in v.items() if kk != "estimates"} for k, v in results.items()}
    path.write_text(json.dumps(slim, indent=2, default=str))
