"""Does sales outreach to product-qualified accounts actually cause conversions?

We simulate a holdout experiment on the top-scored prospect accounts and compare
two designs:

  account-level randomization  whole companies are treated or held out
  user-level randomization     individual users inside the same company are split

In a collaboration product, outreach to one person spills over to colleagues in
the same company (they get pulled into the team pilot). User-level
randomization lets the treatment leak into the control group, so it
underestimates the true effect. Account-level randomization recovers it.

Outcomes are simulated from the planted ground truth; they are illustrative.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRUE_LIFT = {"hot": 0.15, "other": 0.02}   # added conversion probability from outreach
BASE_RATE = {"hot": 0.20, "other": 0.04}   # conversion without outreach


def simulate(accounts: pd.DataFrame, hot_ids: set[str], users_per_account: pd.Series,
             n_runs: int = 400, seed: int = 11) -> dict:
    rng = np.random.default_rng(seed)
    ids = accounts.index.to_numpy()
    is_hot = np.isin(ids, list(hot_ids))
    base = np.where(is_hot, BASE_RATE["hot"], BASE_RATE["other"])
    lift = np.where(is_hot, TRUE_LIFT["hot"], TRUE_LIFT["other"])
    true_effect = float(lift.mean())
    sizes = users_per_account.reindex(ids).fillna(5).astype(int).to_numpy()

    acct_est, user_est = [], []
    for _ in range(n_runs):
        # Account-level design
        treat = rng.random(ids.size) < 0.5
        conv = rng.random(ids.size) < base + lift * treat
        acct_est.append(conv[treat].mean() - conv[~treat].mean())

        # User-level design: half the users in every account are contacted, so
        # every account is exposed; conversion is a company decision that lands
        # on all its users, treated or not.
        # A small direct effect remains: a contacted user is a bit likelier to
        # upgrade on their own even if the company doesn't sign.
        conv_u = rng.random(ids.size) < base + lift  # every account exposed
        t_users, c_users = [], []
        for k, c in zip(sizes, conv_u):
            t = rng.random(k) < 0.5
            own = rng.random(k) < np.where(t, 0.03, 0.01)
            out = c | own
            t_users.append(out[t])
            c_users.append(out[~t])
        tu, cu = np.concatenate(t_users), np.concatenate(c_users)
        user_est.append(tu.mean() - cu.mean())

    def summ(x):
        x = np.array(x)
        return {"mean": round(float(x.mean()), 3),
                "p05": round(float(np.percentile(x, 5)), 3),
                "p95": round(float(np.percentile(x, 95)), 3)}

    a, u = summ(acct_est), summ(user_est)
    return {
        "question": "Does outreach to product-qualified accounts cause conversions, and how should we test it?",
        "accounts_in_test": int(ids.size), "hot_accounts_in_test": int(is_hot.sum()),
        "true_effect": round(true_effect, 3),
        "account_level_estimate": a, "user_level_estimate": u,
        "estimates": {"account": acct_est, "user": user_est},
        "finding": (f"Randomizing by account recovers the true lift (~{a['mean']:+.0%} vs a true "
                    f"{true_effect:+.0%}). Randomizing users inside the same company shows ~{u['mean']:+.0%}, "
                    "because colleagues share the outcome. Test sales plays at the account level, "
                    "and keep a standing holdout so outreach can prove its own lift."),
    }
