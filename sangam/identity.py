"""Identity resolution: tie each user to a company, or say honestly that we can't.

Enterprise users arrive through a corporate directory (SSO), so their company is
known. Self-serve users arrive with a personal sign-in, and the only clue is the
email domain. Three outcomes:

  directory        enterprise SSO user, company known from the directory
  domain_match     self-serve user whose email domain matches a known company
  personal_domain  gmail.com and similar: cannot be tied to a company
  private_relay    Apple "Hide My Email" relay address: cannot be tied to a company
"""

from __future__ import annotations

import pandas as pd

from .generate import PERSONAL_DOMAINS, RELAY_DOMAIN


def resolve(users: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    by_domain = accounts.set_index("domain").account_id
    out = users.copy()
    out["account_id"] = out.email_domain.map(by_domain)
    out["resolution"] = "domain_match"
    out.loc[out.channel == "enterprise", "resolution"] = "directory"
    out.loc[out.email_domain.isin(PERSONAL_DOMAINS), "resolution"] = "personal_domain"
    out.loc[out.email_domain == RELAY_DOMAIN, "resolution"] = "private_relay"
    out.loc[out.resolution.isin(["personal_domain", "private_relay"]), "account_id"] = None
    return out


def resolution_summary(resolved: pd.DataFrame) -> pd.DataFrame:
    ss = resolved[resolved.channel == "self_serve"]
    t = (ss.groupby(["provider", "resolution"]).size().unstack(fill_value=0))
    t["total"] = t.sum(axis=1)
    t["resolved_share"] = (t.get("domain_match", 0) / t.total).round(3)
    return t.sort_values("total", ascending=False)
