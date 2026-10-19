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


def find_threshold(r: pd.DataFrame, min_flagged: int = 15) -> dict:
    """Search simple, explainable trigger rules and keep the best by F1."""
    y = r.converted.astype(bool)
    best = None
    for k in range(1, 13):
        for f in range(1, 5):
            flag = (r.activated >= k) & (r.functions >= f)
            if flag.sum() < min_flagged:
                continue
            s = _rule_stats(flag, y) | {"min_activated": k, "min_functions": f}
            if best is None or s["f1"] > best["f1"]:
                best = s
    # Naive alternative: count sign-ups, the number most dashboards show.
    naive = None
    for k in range(1, 40):
        flag = r.signups >= k
        if flag.sum() < min_flagged:
            continue
        s = _rule_stats(flag, y) | {"min_signups": k}
        if naive is None or s["f1"] > naive["f1"]:
            naive = s
    base = round(float(y.mean()), 3)
    lift = round(best["precision"] / base, 1) if base else None
    return {
        "question": "How many independent adopters should a company have before we start an enterprise sales motion?",
        "baseline_conversion": base,
        "recommended_rule": best,
        "signup_count_rule": naive,
        "lift_over_baseline": lift,
        "finding": (
            f"Trigger an enterprise sales motion when a company has at least {best['min_activated']} "
            f"activated independent users across {best['min_functions']}+ functions. Those accounts convert at "
            f"{best['precision']:.0%} versus a {base:.0%} baseline ({lift}x), and the rule captures "
            f"{best['recall']:.0%} of contracts while flagging {best['accounts_flagged']} accounts. "
            f"The best rule built on raw sign-up counts scores F1 {naive['f1']:.2f} against "
            f"{best['f1']:.2f}: sign-ups include event spikes that never activate."),
        "caveat": ("Counts only users resolvable to a company by email domain; private-relay and personal "
                   "addresses are invisible, so the true number of adopters is higher. Re-fit the rule each "
                   "quarter against new outcomes."),
    }


# ---------- channel ranking ----------

def channel_ranking(ds: Dataset, ready_accounts: set[str], outcomes: pd.DataFrame) -> dict:
    """Rank self-serve acquisition channels by volume, retention and pipeline.

    Accounts are credited to the channel that brought their *first* sign-up
    (first-touch). That is a choice, stated so it can be challenged."""
    u = ds.users[ds.users.channel == "self_serve"].copy()
    u["w8"] = ds.activity.loc[u.user_id, W].to_numpy()
    g = u.groupby("source")
    t = pd.DataFrame({
        "signups": g.size(),
        "activation_rate": g.activated_agent.mean(),
        "w8_retention": g.w8.mean(),
        "company_resolved": g.account_id.apply(lambda s: s.notna().mean()),
    })
    first = (u[u.account_id.notna()].sort_values(["signup_week", "user_id"])
             .groupby("account_id").source.first())
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
        "finding": (
            f"Rankings disagree. '{vol}' brings the most sign-ups, but '{top}' produces the most sales-ready "
            f"accounts per 1,000 sign-ups ({t.loc[top, 'ready_per_1k']}) and retains "
            f"{t.loc[top, 'w8_retention']:.0%} at week 8. '{worst[0]}' and '{worst[1]}' retain worst. "
            "Invest in invite loops and work-identity channels for pipeline; judge broad social channels on "
            f"retained users, not sign-ups. Pipeline ranks for {', '.join(repr(x) for x in thin)} rest on fewer "
            "than 5 accounts each; treat their order as noise."),
        "caveat": "Channels and intent are entangled: invited users arrive with a colleague's context. Test channel spend with geo or time holdouts before reallocating budget.",
    }
