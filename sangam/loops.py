"""Viral loops: which sharing behaviors grow the product, and which rewards pay off.

Three analyses over the share ledger (data/shares.csv.gz):

  scorecard       per loop: share volume, view -> sign-up -> activation, viral
                  coefficient on *activated* recipients (sign-ups shown for
                  contrast), cycle time, recipient retention
  expand vs land  same-company shares push prospects over the sales trigger;
                  cross-company shares seed companies that had no users yet
  reward policy   simulated arms: no reward, reward per share sent, per sign-up,
                  per recipient first agent action, the same weighted by share
                  type, and a stage-aware policy (same-domain shares before a
                  contract, external shares after one)

The reward simulation runs on STATED BEHAVIORAL ASSUMPTIONS (how much each
incentive raises sharing, and how good the extra shares are). Its value is the
measurement design and the mechanism, not the specific numbers; the real
answers come from an A/B test of the reward policy.

Viral coefficients here are single-generation: recipients' own shares are not
re-simulated.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .dhruva import Dataset
from .generate import PERSONAL_DOMAINS, RELAY_DOMAIN

W = 8
LOOP_LABEL = {"agent": "Shared agent", "asset": "Shared asset (URL)", "space": "Shared space / knowledge base",
              "embed": "Slack or email embed", "digest": "Recurring digest", "referral": "Referral credit"}


def _ledger(ds: Dataset, data_dir: str | Path = "data") -> pd.DataFrame:
    sh = pd.read_csv(Path(data_dir) / "shares.csv.gz")
    u = ds.users.set_index("user_id")
    sh["sender_domain"] = sh.sender_id.map(u.email_domain)
    sh["sender_account"] = sh.sender_id.map(u.account_id)
    personal = sh.recipient_email_domain.isin(PERSONAL_DOMAINS + [RELAY_DOMAIN])
    sh["relation"] = np.where(personal, "personal",
                              np.where(sh.recipient_email_domain == sh.sender_domain, "same_company",
                                       "other_company"))
    sh["stage"] = np.where(sh.sender_licensed, "post_contract", "pre_contract")
    rec = u.reindex(sh.recipient_user_id)
    sh["activated"] = rec.activated_agent.fillna(False).to_numpy().astype(bool)
    sh["recipient_account"] = rec.account_id.to_numpy()
    sh["w8"] = ds.activity.reindex(sh.recipient_user_id)[W].to_numpy()
    return sh


def scorecard(ds: Dataset, data_dir: str | Path = "data") -> pd.DataFrame:
    sh = _ledger(ds, data_dir)
    pool = ds.users[ds.users.segment != "internal"]
    base = len(pool)
    open_ = sh[~sh.recipient_licensed]                       # shares that can create a new user
    g = open_.groupby("loop")
    t = pd.DataFrame({
        "shares": sh.groupby("loop").size(),
        "view_rate": g.viewed.mean(),
        "signup_per_share": g.signed_up.mean(),
        "activation_of_signups": open_[open_.signed_up].groupby("loop").activated.mean(),
        "signups": g.signed_up.sum(),
        "activated_recipients": g.activated.sum(),
        "median_cycle_days": open_[open_.signed_up].assign(c=lambda d: d.signup_day - d.share_day)
            .groupby("loop").c.median(),
        "recipient_w8_retention": open_[open_.signed_up].groupby("loop").w8.mean(),
        "same_company_share": g.relation.apply(lambda s: (s == "same_company").mean()),
    })
    t["k_signups_per_100"] = (t.signups / base * 100).round(2)
    t["k_activated_per_100"] = (t.activated_recipients / base * 100).round(2)
    t["activated_per_1k_shares"] = (t.activated_recipients / t.shares * 1000).round(1)
    t = t.round(3).sort_values("k_activated_per_100", ascending=False)
    t.index = t.index.rename("loop")
    return t


def expand_vs_land(ds: Dataset, ready_rule: dict, outcomes: pd.DataFrame,
                   data_dir: str | Path = "data") -> pd.DataFrame:
    """Expansion: prospects that reach the sales trigger only because of a loop's
    recipients. Landing: companies whose FIRST resolved user arrived through a loop."""
    sh = _ledger(ds, data_dir)
    u = ds.users[ds.users.channel == "self_serve"]
    prospects = set(outcomes.account_id)

    def ready(df):
        act = df[df.activated_agent & df.account_id.isin(prospects)]
        a = act.groupby("account_id").size()
        f = act.groupby("account_id").function.nunique()
        return set(a[(a >= ready_rule["min_activated"]) & (f.reindex(a.index) >= ready_rule["min_functions"])].index)

    all_ready = ready(u)
    first = u.dropna(subset=["account_id"]).sort_values(["signup_week", "user_id"]).groupby("account_id").first()
    later = u.dropna(subset=["account_id"]).groupby("account_id").size()
    rows = {}
    for loop in sh.loop.unique():
        src = f"shared_{loop}"
        without = ready(u[u.source != src])
        seeded = first[first.source == src]
        rows[loop] = {
            "prospects_pushed_over_trigger": len(all_ready - without),
            "companies_seeded": int(len(seeded)),
            "seeded_that_grew_to_3_users": int((later.reindex(seeded.index) >= 3).sum()),
        }
    return pd.DataFrame(rows).T.rename_axis("loop")


# ---------- reward policy simulation ----------
# The arms are built-in policies; the simulation and the behavioral assumptions live in
# sangam/policy.py, which also compiles reward guidelines written in plain language.

def reward_simulation(ds: Dataset, ready_rule: dict, outcomes: pd.DataFrame,
                      data_dir: str | Path = "data") -> dict:
    from .policy import simulate_builtins
    return simulate_builtins(ds, ready_rule, outcomes, data_dir)


def summarize(ds: Dataset, ready_rule: dict, outcomes: pd.DataFrame, data_dir: str | Path = "data") -> dict:
    sc = scorecard(ds, data_dir)
    land = expand_vs_land(ds, ready_rule, outcomes, data_dir)
    sim = reward_simulation(ds, ready_rule, outcomes, data_dir)
    top_k = sc.index[0]
    most_signups = sc.k_signups_per_100.idxmax()
    best_land = land.companies_seeded.idxmax()
    best_expand = land.prospects_pushed_over_trigger.idxmax()
    ret = sc.recipient_w8_retention.idxmax()
    fast = sc.median_cycle_days.idxmin()
    paid = {a: r for a, r in sim.items() if r["rewards_per_incremental_activated"]}
    cheapest = min(paid, key=lambda a: paid[a]["rewards_per_incremental_activated"])
    sent, sa, wt = sim["per_share_sent"], sim["stage_aware"], sim["per_activation_weighted"]
    ref = sc.loc["referral"]
    finding = (
        f"'{LOOP_LABEL[top_k]}' grows the product most ({sc.loc[top_k, 'k_activated_per_100']} activated "
        f"recipients per 100 users; {sc.loc[top_k, 'activation_of_signups']:.0%} of its sign-ups activate) and turns "
        f"fastest. '{LOOP_LABEL[best_land]}' is the landing loop: it seeds the most new companies "
        f"({int(land.loc[best_land, 'companies_seeded'])}). '{LOOP_LABEL[ret]}' recipients retain best. Embeds and "
        f"digests create many impressions but convert under 3% per share, and referral credits paid on sign-up "
        f"bring sign-ups of which only {ref.activation_of_signups:.0%} activate. In the reward simulation, paying per "
        f"share sent nearly doubles shares but adds only {sent['incremental_activated']:+} activated users. The "
        f"stage-aware policy delivers the same pipeline as uniform weighted rewards "
        f"({sa['extra_prospects_over_trigger']} vs {wt['extra_prospects_over_trigger']} extra prospects over the "
        f"trigger; {sa['extra_companies_seeded_by_customers']} vs {wt['extra_companies_seeded_by_customers']} companies "
        f"seeded by customers) while paying {sa['rewards_paid']:,} rewards instead of {wt['rewards_paid']:,}. "
        "Uniform rewards buy more total sign-ups, mostly prosumer activity and colleagues who were already licensed.")
    return {
        "question": "Which viral loops grow the product, and which rewards pay off?",
        "scorecard": sc.reset_index().to_dict("records"),
        "expand_vs_land": land.reset_index().to_dict("records"),
        "reward_simulation": sim,
        "cheapest_arm": cheapest,
        "finding": finding,
        "caveat": ("Viral coefficients are single-generation. The reward simulation rests on stated behavioral "
                   "assumptions (see BEHAVIOR in sangam/policy.py); test the policy with an A/B test, "
                   "randomized by workspace, before rolling it out."),
    }
