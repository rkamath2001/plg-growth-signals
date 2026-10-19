"""Product-qualified accounts (PQAs): companies where independent adopters are
signaling an enterprise deal, each scored with plain-language reasons and a
recommended play.

The score is deliberately transparent: points for each signal, so a seller can
see *why* an account is on the list. Noise filters remove signup bursts that
look like demand but aren't (a single webinar, one function, no activation).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .dhruva import Dataset

RECENT_WEEKS = 4  # "currently active" = active in any of the last 4 observed weeks


def account_rollup(ds: Dataset) -> pd.DataFrame:
    u = ds.users[(ds.users.channel == "self_serve") & ds.users.account_id.notna()].copy()
    last = ds.events.week.max()
    recent = ds.events[(ds.events.week > last - RECENT_WEEKS)
                       & ds.events.event_type.isin(["question_asked", "agent_action"])]
    u["recently_active"] = u.user_id.isin(set(recent.user_id))
    g = u.groupby("account_id")
    roll = pd.DataFrame({
        "users": g.size(),
        "functions": g.function.nunique(),
        "activated_share": g.activated_agent.mean(),
        "recently_active": g.recently_active.sum(),
        "sharers": g.apply(lambda x: (x.agent_shared_w0 > 0).sum(), include_groups=False),
        "inviters": g.apply(lambda x: (x.teammate_invited_w0 > 0).sum(), include_groups=False),
        "plus_users": g.apply(lambda x: ((x.plan == "plus") | x.upgraded).sum(), include_groups=False),
        "peak_week_share": g.signup_week.agg(lambda s: s.value_counts(normalize=True).iloc[0]),
    })
    roll["recently_active_share"] = roll.recently_active / roll.users
    acc = ds.accounts.set_index("account_id")
    roll = roll.join(acc[["company", "domain", "industry", "size_band", "has_account_team"]])
    contract_ids = set(ds.users.loc[ds.users.segment == "enterprise_external", "account_id"])
    roll["is_customer"] = roll.index.isin(contract_ids)
    return roll


def score(roll: pd.DataFrame) -> pd.DataFrame:
    r = roll.copy()
    pts = pd.DataFrame(index=r.index)
    pts["breadth"] = np.where(r.functions >= 3, 25, np.where(r.functions == 2, 10, 0))
    pts["scale"] = np.clip(r.users, 0, 20) * 1.0
    pts["activation"] = (r.activated_share * 25).round(1)
    pts["retention"] = (r.recently_active_share * 20).round(1)
    pts["collaboration"] = np.clip(r.sharers * 4 + r.inviters * 2, 0, 15)
    pts["paid_intent"] = np.clip(r.plus_users * 3, 0, 10)
    r["score"] = pts.sum(axis=1).round(1)

    # Noise: most signups in one week, little activation. Classic event spike.
    r["noise_flag"] = (r.peak_week_share >= 0.6) & (r.activated_share < 0.35) & (r.users >= 8)
    r.loc[r.noise_flag, "score"] = (r.loc[r.noise_flag, "score"] * 0.3).round(1)
    r["min_signal"] = r.users >= 5  # below this, a pattern is anecdote

    def reasons(row) -> str:
        bits = [f"{row.users} independent users across {row.functions} functions",
                f"{row.activated_share:.0%} completed an agent action in week 0",
                f"{row.recently_active_share:.0%} active in the last {RECENT_WEEKS} weeks"]
        if row.sharers:
            bits.append(f"{row.sharers} shared agents with colleagues")
        if row.plus_users:
            bits.append(f"{row.plus_users} on a paid plan")
        if row.noise_flag:
            bits.append(f"NOISE: {row.peak_week_share:.0%} signed up in one week with low activation")
        return "; ".join(bits)

    def play(row) -> str:
        if row.noise_flag:
            return "Nurture: in-product onboarding only; no sales touch"
        if not row.min_signal:
            return "Watch: too few users to act on"
        if row.is_customer:
            return "Expansion: alert the customer's admin and account team to unmanaged adopters"
        if row.score >= 60 and row.has_account_team:
            return "Route to existing cloud account team: propose an enterprise pilot"
        if row.score >= 60:
            return "Business development: offer a team pilot with admin controls"
        if row.score >= 40:
            return "Champion enablement: in-product prompts to share agents and invite a team"
        return "Self-serve: standard lifecycle messaging"

    r["reasons"] = r.apply(reasons, axis=1)
    r["play"] = r.apply(play, axis=1)
    cols = ["company", "industry", "size_band", "score", "play", "reasons", "users", "functions",
            "activated_share", "recently_active_share", "sharers", "plus_users",
            "peak_week_share", "noise_flag", "min_signal", "is_customer", "has_account_team"]
    return r[cols].sort_values("score", ascending=False)


def top_accounts(ds: Dataset, n: int = 20, prospects_only: bool = True) -> pd.DataFrame:
    s = score(account_rollup(ds))
    if prospects_only:
        s = s[~s.is_customer]
    return s.head(n)
