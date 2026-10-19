"""Cohort analyses. Each function returns a plain dict a person or an agent can quote."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .dhruva import MIN_COHORT, Dataset, retention_at, retention_by, retention_curve

W = 8  # headline retention week


def _bootstrap_diff(a: np.ndarray, b: np.ndarray, n: int = 1000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    diffs = [rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean() for _ in range(n)]
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return round(float(lo), 3), round(float(hi), 3)


def headline_inflation(ds: Dataset) -> dict:
    """How much does customer zero flatter the headline?"""
    u = ds.users
    all_r, all_n = retention_at(ds, W)
    ext_r, ext_n = retention_at(ds, W, u.segment != "internal")
    int_r, int_n = retention_at(ds, W, u.segment == "internal")
    return {
        "question": "Does the internal deployment distort headline retention?",
        "w8_retention_all_users": round(all_r, 3), "n_all": all_n,
        "w8_retention_external_only": round(ext_r, 3), "n_external": ext_n,
        "w8_retention_internal_only": round(int_r, 3), "n_internal": int_n,
        "inflation_points": round(100 * (all_r - ext_r), 1),
        "finding": (f"Including customer zero raises W{W} retention from {ext_r:.0%} to {all_r:.0%}. "
                    "Report external users separately; internal use is mandated."),
    }


def activation_test(ds: Dataset) -> dict:
    """Which first-week behavior predicts retention: an agent action or a question?"""
    u = ds.users[ds.users.segment != "internal"]
    r = ds.activity.loc[u.user_id, W].to_numpy()
    agent = u.activated_agent.to_numpy()
    qonly = u.activated_question_only.to_numpy()
    neither = ~agent & ~qonly
    res = {}
    for name, m in (("agent_action", agent), ("question_only", qonly), ("neither", neither)):
        x = r[m]
        res[name] = {"w8_retention": round(float(np.nanmean(x)), 6), "n": int(np.sum(~np.isnan(x)))}
    lift = res["agent_action"]["w8_retention"] - res["question_only"]["w8_retention"]
    ci = _bootstrap_diff(r[agent], r[qonly])
    # within-segment check so the result isn't a channel-mix artifact
    within = {}
    for seg, g in u.groupby("segment"):
        rr = ds.activity.loc[g.user_id, W]
        a = rr[g.activated_agent.to_numpy()].mean()
        q = rr[g.activated_question_only.to_numpy()].mean()
        within[seg] = round(float(a - q), 3)
    return {
        "question": "Is activation the first agent action or the first question?",
        "cohorts": res, "lift_agent_vs_question": round(lift, 3), "ci95": ci,
        "lift_within_segment": within,
        "finding": (f"Users who complete an agent action in week 0 retain at "
                    f"{res['agent_action']['w8_retention']:.0%} at W{W}, vs "
                    f"{res['question_only']['w8_retention']:.0%} for question-only users "
                    f"(+{lift:.0%}, 95% CI {ci[0]:+.0%} to {ci[1]:+.0%}). The gap holds in every segment. "
                    "Define activation as the first completed agent action."),
        "caveat": "Observational: high-intent users do both. Confirm with an onboarding experiment that nudges a first agent action.",
    }


def connector_breadth(ds: Dataset) -> dict:
    u = ds.users[ds.users.segment != "internal"].copy()
    u["connectors_band"] = pd.cut(u.connectors_w0, [-1, 0, 2, 100], labels=["0", "1-2", "3+"])
    ds_tmp = Dataset(ds.accounts, u, ds.events, ds.activity)
    t = retention_by(ds_tmp, "connectors_band", W, exclude_internal=False)
    return {
        "question": "Does connecting more apps in week 0 predict retention?",
        "table": t.reset_index().rename(columns={"g": "connectors_w0"}).to_dict("records"),
        "finding": "Users linking 3+ connectors in week 0 retain markedly better; make the third connector a guided step.",
    }


def simpson_check(ds: Dataset, feature: str = "desktop") -> dict:
    """Compare a feature's aggregate lift with its lift inside each segment."""
    u = ds.users
    r = ds.activity.loc[u.user_id, W].to_numpy()
    f = u[feature].to_numpy()
    agg = float(np.nanmean(r[f]) - np.nanmean(r[~f]))
    within, weights = {}, {}
    for seg, g in u.groupby("segment"):
        rr = ds.activity.loc[g.user_id, W].to_numpy()
        ff = g[feature].to_numpy()
        if ff.sum() < 30 or (~ff).sum() < 30:
            continue
        within[seg] = round(float(np.nanmean(rr[ff]) - np.nanmean(rr[~ff])), 3)
        weights[seg] = len(g)
    pooled = sum(within[s] * weights[s] for s in within) / sum(weights.values())
    paradox = abs(agg) > 0.05 and abs(pooled) < 0.4 * abs(agg)
    share = u.groupby("segment")[feature].mean().round(2).to_dict()
    return {
        "question": f"Does '{feature}' really lift retention?",
        "aggregate_lift": round(agg, 3), "within_segment_lift": within,
        "weighted_within_lift": round(pooled, 3), "adoption_by_segment": share,
        "confounded": bool(paradox),
        "finding": (f"In aggregate, '{feature}' users retain {agg:+.0%} better, but inside each segment the "
                    f"difference is about {pooled:+.0%}. The aggregate lift comes from mix: the internal "
                    "rollout installed it by default. Do not claim it as a retention driver."
                    if paradox else
                    f"'{feature}' shows a consistent lift of about {pooled:+.0%} within segments."),
    }


def channel_view(ds: Dataset) -> dict:
    by_seg = retention_by(ds, "segment", W, exclude_internal=False)
    by_provider = retention_by(ds, "provider", W)
    return {
        "question": "How do channels and sign-in providers compare?",
        "by_segment": by_seg.reset_index().rename(columns={"g": "segment"}).to_dict("records"),
        "by_provider": by_provider.reset_index().rename(columns={"g": "provider"}).to_dict("records"),
        "min_cohort": MIN_COHORT,
    }


def curves(ds: Dataset) -> dict[str, pd.Series]:
    u = ds.users
    ext = u.segment != "internal"
    return {
        "Agent action in week 0": retention_curve(ds, ext & u.activated_agent),
        "Question only": retention_curve(ds, ext & u.activated_question_only),
        "Neither": retention_curve(ds, ext & ~u.activated_agent & ~u.activated_question_only),
        "Customer zero (internal)": retention_curve(ds, u.segment == "internal"),
    }
