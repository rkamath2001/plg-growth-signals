"""The funnel over time, and the path from one adopter to an enterprise account.

  funnel        self-serve users from sign-up to week 8, and prospect companies
                from first user to contract
  cohorts       activation and retention by sign-up week; share of sign-ups that
                arrive through shares or invites
  engagement    weekly active users, agent-active users, agent actions per user,
                weeks active out of the first 8
  expansion     how long companies take to go from their first activated user to
                the trigger, and how later colleagues arrive
  champions     whether a company's first activated user shared early, and how
                that relates to reaching the trigger and buying
  virality      activated recipients per activated user, overall

All of it is observational. Weeks beyond the observation window are unknown, not
inactive, so late cohorts have no week-8 value and late companies are still in
progress.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .dhruva import Dataset
from .loops import _ledger

SHARED = ("shared_agent", "shared_asset", "shared_space", "shared_embed", "shared_digest",
          "shared_referral", "teammate_invite")


def _self_serve(ds: Dataset) -> pd.DataFrame:
    return ds.users[ds.users.segment == "self_serve"]


def funnel(ds: Dataset, outcomes: pd.DataFrame, k: int) -> dict:
    ss = _self_serve(ds)
    a = ds.activity.loc[ss.user_id]
    users = {"signed_up": len(ss), "activated_week0": round(float(ss.activated_agent.mean()), 3),
             "active_week1": round(float(a[1].mean()), 3), "active_week4": round(float(a[4].mean()), 3),
             "active_week8": round(float(a[8].mean()), 3), "tied_to_company": round(float(ss.account_id.notna().mean()), 3),
             "upgraded_to_paid": round(float(ss.upgraded.mean()), 3)}
    oc = outcomes.set_index("account_id").converted_to_contract
    p = ss[ss.account_id.isin(oc.index)]
    act = p[p.activated_agent].groupby("account_id").size().reindex(oc.index).fillna(0)
    anyu = p.groupby("account_id").size().reindex(oc.index).fillna(0)
    companies = {"prospects": len(oc), "with_a_user": int((anyu > 0).sum()), "with_an_activated_user": int((act >= 1).sum()),
                 f"at_{k - 1}_activated": int((act >= k - 1).sum()), f"at_trigger_{k}": int((act >= k).sum()),
                 "contracts": int(oc.sum()), "contracts_from_trigger_companies": int(oc[act >= k].sum())}
    return {"users": users, "companies": companies}


def cohorts(ds: Dataset) -> pd.DataFrame:
    ss = _self_serve(ds)
    a = ds.activity.loc[ss.user_id]
    t = ss.assign(w1=a[1].to_numpy(), w4=a[4].to_numpy(), w8=a[8].to_numpy(),
                  via_share=ss.source.isin(SHARED))
    g = t.groupby("signup_week").agg(signups=("user_id", "size"), activated=("activated_agent", "mean"),
                                     week1=("w1", "mean"), week4=("w4", "mean"), week8=("w8", "mean"),
                                     via_share_or_invite=("via_share", "mean"))
    return g.round(3)


def engagement(ds: Dataset) -> pd.DataFrame:
    ext = ds.users.loc[ds.users.segment != "internal", "user_id"]
    e = ds.events[ds.events.user_id.isin(ext)]
    active = e[e.event_type.isin(["agent_action", "question_asked"])].groupby("week").user_id.nunique()
    agent = e[e.event_type == "agent_action"]
    agent_users = agent.groupby("week").user_id.nunique()
    per = agent.groupby("week")["count"].sum() / agent_users
    return pd.DataFrame({"weekly_active": active, "agent_active": agent_users,
                         "agent_share_of_active": (agent_users / active).round(3),
                         "agent_actions_per_agent_active_user": per.round(2)}).fillna(0)


def weeks_active(ds: Dataset) -> dict:
    ss = _self_serve(ds)
    out = {}
    for name, m in (("activated", ss.activated_agent), ("question_only", ss.activated_question_only)):
        a = ds.activity.loc[ss.loc[m, "user_id"], list(range(1, 9))]
        out[name] = round(float(a.mean(axis=1).mean() * 8), 1)
    return out


def _activated_at_prospects(ds: Dataset, outcomes: pd.DataFrame) -> pd.DataFrame:
    ss = _self_serve(ds)
    act = ss[ss.activated_agent & ss.account_id.isin(set(outcomes.account_id))]
    act = act.sort_values(["account_id", "signup_week", "user_id"]).copy()
    act["rank"] = act.groupby("account_id").cumcount() + 1
    return act


def expansion(ds: Dataset, outcomes: pd.DataFrame, k: int) -> dict:
    act = _activated_at_prospects(ds, outcomes)
    first = act[act["rank"] == 1].set_index("account_id")
    kth = act[act["rank"] == k].set_index("account_id")
    weeks = kth.signup_week - first.reindex(kth.index).signup_week
    ss = _self_serve(ds)
    ready = set(kth.index)
    later = ss[ss.account_id.isin(ready) & ~ss.user_id.isin(first.user_id)]
    rest = ss[ss.account_id.isin(set(outcomes.account_id) - ready)]
    return {"companies_at_trigger": len(kth), "weeks_first_to_trigger_median": float(weeks.median()),
            "weeks_p25": float(weeks.quantile(.25)), "weeks_p75": float(weeks.quantile(.75)),
            "later_colleagues_via_share_or_invite": round(float(later.source.isin(SHARED).mean()), 3),
            "users_via_share_or_invite_elsewhere": round(float(rest.source.isin(SHARED).mean()), 3)}


def champions(ds: Dataset, outcomes: pd.DataFrame, k: int, within_weeks: int = 2) -> dict:
    act = _activated_at_prospects(ds, outcomes)
    first = act[act["rank"] == 1].set_index("account_id")
    ev = ds.events[ds.events.event_type.isin(["agent_shared", "teammate_invited"])]
    ev = ev.merge(ds.users[["user_id", "signup_week"]], on="user_id")
    early = set(ev.loc[(ev.week - ev.signup_week) <= within_weeks, "user_id"])
    first["shared_early"] = first.user_id.isin(early)
    oc = outcomes.set_index("account_id").converted_to_contract.reindex(first.index)
    n = act.groupby("account_id").size().reindex(first.index)
    tier = pd.cut(n, [0, k - 2, k - 1, 10 ** 9], labels=["below", "one_short", "at_trigger"])
    return {"contract_rate_if_champion_shared_early": round(float(oc[first.shared_early].mean()), 3),
            "contract_rate_otherwise": round(float(oc[~first.shared_early].mean()), 3),
            "companies_champion_shared": int(first.shared_early.sum()),
            "companies_champion_did_not": int((~first.shared_early).sum()),
            "share_of_champions_sharing_early_by_tier": first.groupby(tier, observed=False).shared_early.mean().round(3).to_dict()}


def virality(ds: Dataset, data_dir: str | Path = "data") -> dict:
    sh = _ledger(ds, data_dir)
    ext = ds.users[ds.users.segment != "internal"]
    activated = ext[ext.activated_agent]
    return {"activated_recipients_per_100_activated_users": round(float(sh.activated.sum() / len(activated) * 100), 1),
            "activated_users_who_shared": round(float(activated.user_id.isin(set(sh.sender_id)).mean()), 3)}


def summarize(ds: Dataset, outcomes: pd.DataFrame, k: int, data_dir: str | Path = "data") -> dict:
    eng = engagement(ds)
    return {"funnel": funnel(ds, outcomes, k), "cohorts": cohorts(ds).reset_index().to_dict("records"),
            "engagement": eng.reset_index().to_dict("records"), "weeks_active_of_first_8": weeks_active(ds),
            "expansion": expansion(ds, outcomes, k), "champions": champions(ds, outcomes, k),
            "virality": virality(ds, data_dir)}
