"""From signals to sales motions.

Two questions a growth leader asks every week:

  1. Which acquisition channels bring users who matter? Ranked three ways,
     because volume, retention and pipeline give different answers.
  2. How many independent freemium adopters does a company need before a
     sales motion pays off? Learned from observed contract outcomes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .dhruva import MIN_COHORT, Dataset

W = 8


# ---------- sales-trigger threshold ----------

def prospect_rollup(ds: Dataset, outcomes: pd.DataFrame) -> pd.DataFrame:
    """Per prospect company, what we can observe: sign-ups, activated users and
    the functions they span. Only users resolved by email domain are counted."""
    u = ds.users[(ds.users.channel == "self_serve") & ds.users.account_id.notna()]
    act = u[u.activated_agent]
    r = pd.DataFrame({
        "signups": u.groupby("account_id").size(),
        "activated": act.groupby("account_id").size(),
        "functions": act.groupby("account_id").function.nunique(),
    })
    out = outcomes.set_index("account_id")
    r = r.reindex(out.index).fillna(0).astype(int)
    r["converted"] = out.converted_to_contract
    return r


def conversion_by_activated(r: pd.DataFrame) -> pd.DataFrame:
    """Conversion by activated users; sparse upper counts are grouped so no bar rests on 2-3 accounts."""
    bins = [-1, 0, 1, 2, 3, 4, 7, 10_000]
    labels = ["0", "1", "2", "3", "4", "5-7", "8+"]
    k = pd.cut(r.activated, bins=bins, labels=labels)
    t = r.groupby(k, observed=False).converted.agg(["mean", "size", "sum"])
    t.columns = ["conversion_rate", "accounts", "contracts"]
    return t.round(3)


def _rule_stats(flag: pd.Series, y: pd.Series) -> dict:
    tp = int((flag & y).sum())
    precision = tp / flag.sum() if flag.sum() else 0.0
    recall = tp / y.sum() if y.sum() else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accounts_flagged": int(flag.sum()), "contracts_captured": tp,
            "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def find_threshold(r: pd.DataFrame, min_flagged: int = 15, boots: int = 300, seed: int = 3) -> dict:
    """Pick an explainable trigger rule without over-fitting a small number of contracts.

    Rules have the form "at least k activated users across at least f functions",
    kept canonical (k >= f, since f functions need at least f users). F1 is
    bootstrapped; every rule within one standard error of the best is treated as
    tied, and the simplest tied rule wins (fewest conditions, then highest
    precision, so a small sales team chases fewer, better accounts)."""
    y = r.converted.astype(bool).to_numpy()
    act, fun, n = r.activated.to_numpy(), r.functions.to_numpy(), len(r)
    cands = [(k, f) for k in range(1, 13) for f in range(1, 5)
             if k >= f and ((act >= k) & (fun >= f)).sum() >= min_flagged]
    flags = {c: (act >= c[0]) & (fun >= c[1]) for c in cands}

    def f1(flag, yy):
        tp = (flag & yy).sum()
        return 0.0 if tp == 0 else 2 * tp / (flag.sum() + yy.sum())

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, (boots, n))
    boot = {c: np.array([f1(flags[c][i], y[i]) for i in idx]) for c in cands}
    mean = {c: boot[c].mean() for c in cands}
    best = max(cands, key=lambda c: mean[c])
    se = boot[best].std()
    tied = [c for c in cands if mean[c] >= mean[best] - se]
    yy = pd.Series(y, index=r.index)
    stats = {c: _rule_stats(pd.Series(flags[c], index=r.index), yy) for c in tied}
    pick = min(tied, key=lambda c: (c[1] > 1, -stats[c]["precision"], c[0]))
    rule = stats[pick] | {"min_activated": pick[0], "min_functions": pick[1]}

    naive_best, naive = -1, None
    for k in range(1, 40):
        flag = r.signups >= k
        if flag.sum() < min_flagged:
            continue
        st = _rule_stats(flag, yy) | {"min_signups": k}
        if st["f1"] > naive_best:
            naive_best, naive = st["f1"], st

    base = round(float(y.mean()), 3)
    lift = round(rule["precision"] / base, 1) if base else None
    k = rule["min_activated"]
    warm = r[(r.activated == k - 1)]
    tiers = {
        "sales_motion": {"rule": f"{k}+ activated users", "accounts": rule["accounts_flagged"],
                         "conversion": rule["precision"]},
        "warm_champion": {"rule": f"{k - 1} activated users", "accounts": int(len(warm)),
                          "conversion": round(float(warm.converted.mean()), 3) if len(warm) else None},
        "self_serve": {"rule": f"fewer than {k - 1}", "accounts": int((r.activated < k - 1).sum()),
                       "conversion": round(float(r.loc[r.activated < k - 1, "converted"].mean()), 3)},
    }
    fn_note = ("Requiring a minimum number of functions did not beat the simple count within noise."
               if rule["min_functions"] == 1 else
               f"Requiring {rule['min_functions']}+ functions adds signal beyond the user count.")
    return {
        "question": "How many independent adopters should a company have before we start an enterprise sales motion?",
        "baseline_conversion": base,
        "recommended_rule": rule,
        "tied_rules": [f"{c[0]}+ users across {c[1]}+ functions" for c in sorted(tied)],
        "signup_count_rule": naive,
        "lift_over_baseline": lift,
        "tiers": tiers,
        "finding": (
            f"Start an enterprise sales motion at {k}+ activated independent users. Those companies convert at "
            f"{rule['precision']:.0%} versus a {base:.0%} baseline ({lift}x); the rule captures "
            f"{rule['recall']:.0%} of contracts while flagging {rule['accounts_flagged']} accounts. At {k - 1} activated "
            f"users conversion is {tiers['warm_champion']['conversion']:.0%}: run champion enablement there, not sales. "
            f"{fn_note} The best sign-up-count rule scores F1 {naive['f1']:.2f} against {rule['f1']:.2f}, because "
            "sign-ups include event spikes that never activate."),
        "caveat": (f"Fit on {int(y.sum())} contracts: {len(tied)} rules are statistically tied, so the simplest was "
                   "chosen. Counts only users resolvable to a company by email domain, so the true number of adopters "
                   "is higher. Refit each quarter and by segment as outcomes accumulate."),
    }


# ---------- channel ranking ----------

def channel_ranking(ds: Dataset, ready_accounts: set[str], outcomes: pd.DataFrame) -> dict:
    """Rank self-serve acquisition channels by volume, retention and pipeline.

    Accounts are credited to the channel that brought their *first* sign-up
    (first-touch). That is a choice, stated so it can be challenged."""
    all_ss = ds.users[ds.users.channel == "self_serve"].copy()
    # Loop-sourced users are judged by the loop analysis; first-touch credit would
    # undervalue them, because loops mostly add users to companies already started.
    loop_users = all_ss[all_ss.source.str.startswith("shared_")]
    at_ready = all_ss[all_ss.account_id.isin(ready_accounts) & all_ss.activated_agent]
    loop_share_of_ready_users = float(at_ready.source.str.startswith("shared_").mean()) if len(at_ready) else 0.0
    first_all = (all_ss[all_ss.account_id.notna()].sort_values(["signup_week", "user_id"])
                 .groupby("account_id").source.first())
    ready_first = first_all[first_all.index.isin(ready_accounts)]
    loop_share_of_first_touch = float(ready_first.str.startswith("shared_").mean()) if len(ready_first) else 0.0
    u = all_ss[~all_ss.source.str.startswith("shared_")].copy()
    u["w8"] = ds.activity.loc[u.user_id, W].to_numpy()
    g = u.groupby("source")
    t = pd.DataFrame({
        "signups": g.size(),
        "activation_rate": g.activated_agent.mean(),
        "w8_retention": g.w8.mean(),
        "company_resolved": g.account_id.apply(lambda s: s.notna().mean()),
    })
    first = first_all[~first_all.str.startswith("shared_")]
    won = set(outcomes.loc[outcomes.converted_to_contract, "account_id"])
    t["sales_ready_accounts"] = first[first.index.isin(ready_accounts)].value_counts().reindex(t.index).fillna(0).astype(int)
    t["contracts_sourced"] = first[first.index.isin(won)].value_counts().reindex(t.index).fillna(0).astype(int)
    t["retained_per_100"] = (t.w8_retention * 100).round(1)
    t["ready_per_1k"] = (t.sales_ready_accounts / t.signups * 1000).round(1)
    t["too_small"] = t.signups < MIN_COHORT
    t = t.round(3)

    rank = pd.DataFrame({
        "by_volume": t.signups.rank(ascending=False, method="min").astype(int),
        "by_retention": t.w8_retention.rank(ascending=False, method="min").astype(int),
        "by_pipeline": t.ready_per_1k.rank(ascending=False, method="min").astype(int),
    })
    t = t.join(rank).sort_values("by_pipeline")
    top = t.index[0]
    vol = t.sort_values("by_volume").index[0]
    worst = t.sort_values("w8_retention").index[:2].tolist()
    thin = t.index[t.sales_ready_accounts < 5].tolist()
    return {
        "question": "Which acquisition channels bring users who matter?",
        "table": t.reset_index().rename(columns={"index": "source"}).to_dict("records"),
        "attribution": "first-touch at the account level; last-touch at the user level",
        "loop_users": int(len(loop_users)),
        "loop_share_of_activated_users_at_ready_accounts": round(loop_share_of_ready_users, 3),
        "loop_share_of_first_touch_credit": round(loop_share_of_first_touch, 3),
        "attribution_note": (
            f"Viral-loop recipients are {loop_share_of_ready_users:.0%} of the activated users at sales-ready "
            f"accounts but get first-touch credit for only {loop_share_of_first_touch:.0%} of those accounts. "
            "First-touch attribution undervalues expansion loops by design, so loops are measured separately, "
            "on the prospects they push over the sales trigger."),
        "finding": (
            f"Rankings disagree. '{vol}' brings the most sign-ups, but '{top}' produces the most sales-ready "
            f"accounts per 1,000 sign-ups ({t.loc[top, 'ready_per_1k']}) and retains "
            f"{t.loc[top, 'w8_retention']:.0%} at week 8. '{worst[0]}' and '{worst[1]}' retain worst. "
            "Invest in invite loops and work-identity channels for pipeline; judge broad social channels on "
            f"retained users, not sign-ups."
            + (f" Pipeline ranks for {', '.join(repr(x) for x in thin)} rest on fewer than 5 accounts"
               f"{' each' if len(thin) > 1 else ''}; treat {'their order' if len(thin) > 1 else 'that rank'} as noise."
               if thin else "")),
        "caveat": "Channels and intent are entangled: invited users arrive with a colleague's context. Test channel spend with geo or time holdouts before reallocating budget.",
    }


# ---------- sign-in providers ----------

def provider_ranking(ds: Dataset, ready_accounts: set[str]) -> dict:
    """Sign-in provider is an identity channel, not an acquisition channel: it
    decides whether we can see which company a user belongs to."""
    u = ds.users[ds.users.channel == "self_serve"].copy()
    u["w8"] = ds.activity.loc[u.user_id, W].to_numpy()
    g = u.groupby("provider")
    t = pd.DataFrame({
        "signups": g.size(),
        "activation_rate": g.activated_agent.mean(),
        "w8_retention": g.w8.mean(),
        "company_resolved": g.account_id.apply(lambda s: s.notna().mean()),
        "private_relay": g.resolution.apply(lambda s: (s == "private_relay").mean()),
    })
    in_ready = u[u.account_id.isin(ready_accounts)]
    t["users_at_ready_accounts"] = in_ready.groupby("provider").size().reindex(t.index).fillna(0).astype(int)
    t["ready_users_per_1k"] = (t.users_at_ready_accounts / t.signups * 1000).round(1)
    t = t.round(3)
    rank = pd.DataFrame({
        "by_volume": t.signups.rank(ascending=False, method="min").astype(int),
        "by_retention": t.w8_retention.rank(ascending=False, method="min").astype(int),
        "by_visibility": t.company_resolved.rank(ascending=False, method="min").astype(int),
        "by_pipeline": t.ready_users_per_1k.rank(ascending=False, method="min").astype(int),
    })
    t = t.join(rank).sort_values("by_pipeline")
    dark = t.sort_values("company_resolved").index[:2].tolist()
    best_ret = t.sort_values("w8_retention", ascending=False).index[0]
    return {
        "question": "How do sign-in providers differ, and what do they hide?",
        "table": t.reset_index().to_dict("records"),
        "finding": (
            f"Provider decides visibility more than quality. {t.loc['google','company_resolved']:.0%} of Google and "
            f"{t.loc['email','company_resolved']:.0%} of email sign-ups can be tied to a company, versus "
            f"{t.loc[dark[0],'company_resolved']:.0%} for '{dark[0]}' and {t.loc[dark[1],'company_resolved']:.0%} for "
            f"'{dark[1]}'. '{best_ret}' users retain best ({t.loc[best_ret,'w8_retention']:.0%}), consistent with a "
            "builder persona. The pipeline ranking mostly mirrors visibility: an account you cannot see never "
            "reaches the sales trigger."),
        "caveat": "Provider retention differences are small and partly persona mix; do not steer users between sign-in options on retention alone.",
    }


def work_email_whatif(ds: Dataset, truth_users: pd.DataFrame, outcomes: pd.DataFrame,
                      rule: dict, uptake: float = 0.3, runs: int = 200, seed: int = 5) -> dict:
    """SIMULATION using ground truth: if a share of hidden adopters added a work
    email (e.g. prompted when they create a shared space), how many more companies
    would cross the sales trigger?"""
    rng = np.random.default_rng(seed)
    prospects = set(outcomes.account_id)
    u = ds.users[ds.users.channel == "self_serve"].merge(
        truth_users[["user_id", "account_id_truth"]], on="user_id")
    hidden = u[u.account_id.isna() & u.account_id_truth.isin(prospects)]
    visible = u[u.account_id.notna() & u.account_id.isin(prospects)]

    def ready(df):
        act = df[df.activated_agent]
        a = act.groupby("acct").size()
        f = act.groupby("acct").function.nunique()
        return set(a[(a >= rule["min_activated"]) & (f.reindex(a.index) >= rule["min_functions"])].index)

    base = ready(visible.assign(acct=visible.account_id))
    full = ready(pd.concat([visible.assign(acct=visible.account_id),
                            hidden.assign(acct=hidden.account_id_truth)]))
    gains = []
    for _ in range(runs):
        take = hidden[rng.random(len(hidden)) < uptake]
        r = ready(pd.concat([visible.assign(acct=visible.account_id), take.assign(acct=take.account_id_truth)]))
        gains.append(len(r - base))
    by_provider = hidden.groupby("provider").size().sort_values(ascending=False).to_dict()
    won = set(outcomes.loc[outcomes.converted_to_contract, "account_id"])
    return {
        "question": "What if hidden adopters added a work email?",
        "hidden_adopters_at_prospects": int(len(hidden)),
        "hidden_by_provider": by_provider,
        "ready_accounts_visible_today": len(base),
        "ready_accounts_if_all_visible": len(full),
        "uptake_assumed": uptake,
        "extra_ready_accounts_at_uptake": round(float(np.mean(gains)), 1),
        "extra_ready_that_converted": len((full - base) & won),
        "finding": (
            f"{len(hidden)} self-serve users at prospect companies are invisible today, mostly via "
            f"{', '.join(list(by_provider)[:2])} sign-ins. If {uptake:.0%} added a work email, about "
            f"{np.mean(gains):.0f} more companies would cross the sales trigger, on top of {len(base)} visible "
            f"today; with full visibility, {len(full) - len(base)} more would. A 'connect your work email to share "
            "with your team' prompt is a pipeline lever, not just an identity feature."),
        "method": "Simulation on synthetic ground truth; real uptake must be measured with an A/B test of the prompt.",
    }
