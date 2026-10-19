"""Connector-derived identity: using the Slack, Teams and Jira workspaces a user
connects as evidence of where they work, without inventing adopters.

A connected workspace is evidence, not proof. An engineer at a bank may connect
their employer's Slack and also their kid's FTC robotics team Slack. A school
workspace named "Ulnex Robotics Boosters" is not Ulnex Holdings. A contractor
may be a guest in a client's workspace. Each would put a user in the wrong
company, and enough of them invent a "cluster of adopters" that isn't there.

Two matchers are compared:

  naive    any workspace whose verified domain, name or name stem matches a company
  guarded  confidence tiers with exclusions:
             high    workspace's verified email domain is the company's domain
             medium  workspace name is the company's full name
             low     name shares only a stem; used only when corroborated by a
                     colleague already resolved by work email
             exclude guest memberships, and community workspaces: very large with
                     no verified domain, or whose connected users already resolve
                     to 3+ different companies (a school, a club, an open community)

Only users we cannot already place by work email are attributed; a work email
always wins over a connector.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .dhruva import Dataset
from .generate import _slug

TIER = {"high": 3, "medium": 2, "low": 1}


def _load(data_dir: str | Path = "data") -> tuple[pd.DataFrame, pd.DataFrame]:
    d = Path(data_dir)
    return pd.read_csv(d / "workspaces.csv"), pd.read_csv(d / "connections.csv")


def _candidates(ws: pd.DataFrame, accounts: pd.DataFrame) -> pd.DataFrame:
    """Every (workspace, company, tier) match before any guard is applied."""
    acc = accounts[~accounts.company.str.contains("(internal)", regex=False)].copy()
    acc["full"] = acc.company.map(_slug)
    acc["stem"] = acc.company.str.split().str[0].map(_slug)
    by_domain = acc.set_index("domain").account_id
    by_full = acc.set_index("full").account_id
    rows = []
    for w in ws.itertuples():
        slug = _slug(str(w.workspace_slug))
        if isinstance(w.verified_domain, str) and w.verified_domain in by_domain.index:
            rows.append((w.workspace_id, by_domain[w.verified_domain], "high"))
            continue
        if slug in by_full.index:
            rows.append((w.workspace_id, by_full[slug], "medium"))
            continue
        hits = acc.loc[acc.stem.str.len().ge(4) & acc.stem.map(lambda s: slug.startswith(s)), "account_id"]
        for aid in hits:
            rows.append((w.workspace_id, aid, "low"))
    return pd.DataFrame(rows, columns=["workspace_id", "account_id", "tier"])


def _links_with_evidence(ds: Dataset, ws: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """Every candidate (user, company) link, annotated with the guards it trips."""
    users = ds.users[ds.users.channel == "self_serve"].set_index("user_id")
    cand = _candidates(ws, ds.accounts)
    lk = links.merge(cand, on="workspace_id")
    lk["email_account"] = lk.user_id.map(users.account_id)

    member = links[~links.is_guest].copy()
    member["email_account"] = member.user_id.map(users.account_id)
    resolved = member.dropna(subset=["email_account"])
    diversity = resolved.groupby("workspace_id").email_account.nunique()
    meta = ws.set_index("workspace_id")
    community = set(diversity[diversity >= 3].index) | set(
        meta[(meta.reported_members > 1000) & meta.verified_domain.isna()].index)
    seen = resolved.groupby("workspace_id").email_account.agg(set)

    lk["community"] = lk.workspace_id.isin(community)
    lk["corroborated"] = [seen.get(w, set()) == {a} for w, a in zip(lk.workspace_id, lk.account_id)]
    lk["rank"] = lk.tier.map(TIER)
    return lk


def _choose(lk: pd.DataFrame, strict: bool) -> pd.DataFrame:
    lk = lk[lk.email_account.isna()]                      # work email always wins
    if lk.empty:
        return lk
    top = lk[lk["rank"] == lk.groupby("user_id")["rank"].transform("max")]
    if strict:                                            # two companies at the same tier: skip
        n = top.groupby("user_id").account_id.nunique()
        top = top[top.user_id.isin(n[n == 1].index)]
    return top.drop_duplicates("user_id")


def attribute(ds: Dataset, ws: pd.DataFrame, links: pd.DataFrame, method: str,
              lk: pd.DataFrame | None = None) -> pd.Series:
    """Map email-unresolved self-serve users to a company via connectors."""
    lk = _links_with_evidence(ds, ws, links) if lk is None else lk
    if method == "guarded":
        lk = lk[~lk.is_guest & ~lk.community & ((lk.tier != "low") | lk.corroborated)]
    return _choose(lk, strict=(method == "guarded")).set_index("user_id").account_id


def _blocked_by(row) -> str:
    if row.is_guest:
        return "guest in another company's workspace"
    if row.community:
        return "community or side-project workspace"
    if row.tier == "low" and not row.corroborated:
        return "name-stem match without a corroborating colleague"
    return "ambiguous or other"


def _ready(users: pd.DataFrame, account_col: pd.Series, prospects: set[str], rule: dict) -> set[str]:
    u = users.assign(acct=account_col.reindex(users.user_id).to_numpy())
    act = u[u.activated_agent & u.acct.isin(prospects)]
    a = act.groupby("acct").size()
    f = act.groupby("acct").function.nunique()
    return set(a[(a >= rule["min_activated"]) & (f.reindex(a.index) >= rule["min_functions"])].index)


def evaluate(ds: Dataset, truth_users: pd.DataFrame, outcomes: pd.DataFrame, rule: dict,
             data_dir: str | Path = "data") -> dict:
    ws, links = _load(data_dir)
    ss = ds.users[ds.users.channel == "self_serve"]
    true_acct = truth_users.set_index("user_id").account_id_truth
    prospects = set(outcomes.account_id)
    email = ss.set_index("user_id").account_id
    hidden = ss[ss.account_id.isna() & ss.user_id.map(true_acct).isin(prospects | set(ds.accounts.account_id))]
    hidden = hidden[hidden.user_id.map(true_acct).notna()]

    truth_ready = _ready(ss, true_acct, prospects, rule)
    base_ready = _ready(ss, email, prospects, rule)
    out = {"hidden_employed_users": int(len(hidden)), "truth_ready_accounts": len(truth_ready),
           "email_only": {"ready_accounts": len(base_ready), "correct_ready": len(base_ready & truth_ready),
                          "phantom_ready": len(base_ready - truth_ready)}}
    examples, blocked = {}, {}
    lk = _links_with_evidence(ds, ws, links)
    naive_pick = _choose(lk, strict=False)
    wrong_pick = naive_pick[naive_pick.account_id != naive_pick.user_id.map(true_acct)]
    blocked = wrong_pick.apply(_blocked_by, axis=1).value_counts().to_dict()
    for method in ("naive", "guarded"):
        att = attribute(ds, ws, links, method, lk)
        correct = (att == att.index.map(true_acct)).sum()
        wrong = len(att) - correct
        combined = email.copy()
        combined.loc[att.index] = att
        ready = _ready(ss, combined, prospects, rule)
        out[method] = {
            "users_attributed": int(len(att)), "correct": int(correct), "wrong": int(wrong),
            "precision": round(correct / len(att), 3) if len(att) else None,
            "recall_of_hidden": round(correct / len(hidden), 3) if len(hidden) else None,
            "ready_accounts": len(ready), "correct_ready": len(ready & truth_ready),
            "phantom_ready": len(ready - truth_ready),
            "new_correct_ready": len((ready - base_ready) & truth_ready),
        }
        if method == "naive":
            bad = att[att != att.index.map(true_acct)]
            ln = links[links.user_id.isin(bad.index)].merge(ws, on="workspace_id")
            ln["to"] = ln.user_id.map(bad)
            ln = ln[ln.apply(lambda r: r.to in set(_candidates(ws[ws.workspace_id == r.workspace_id],
                                                                 ds.accounts).account_id), axis=1)]
            top = ln.groupby("workspace_name").size().sort_values(ascending=False).head(3)
            names = ds.accounts.set_index("account_id").company
            examples = {w: {"users_misattributed": int(n),
                            "attributed_to": names.get(ln[ln.workspace_name == w].to.iloc[0])}
                        for w, n in top.items()}
    n, g = out["naive"], out["guarded"]
    out["naive_false_positive_examples"] = examples
    out["naive_errors_by_guard"] = {k: int(v) for k, v in blocked.items()}
    out["question"] = "Can connected workspaces (Slack, Teams, Jira) reveal where hidden adopters work, without false positives?"
    ex = next(iter(examples.items()), None)
    ex_txt = (f" The worst naive error: '{ex[0]}' put {ex[1]['users_misattributed']} unrelated users into "
              f"{ex[1]['attributed_to']}." if ex else "")
    out["finding"] = (
        f"Naive matching attributes {n['users_attributed']} hidden users at {n['precision']:.0%} precision and "
        f"creates {n['phantom_ready']} phantom sales-ready accounts.{ex_txt} Guarded matching attributes "
        f"{g['users_attributed']} at {g['precision']:.0%} precision, recovers {g['recall_of_hidden']:.0%} of hidden "
        f"employees, and adds {g['new_correct_ready']} genuinely sales-ready accounts with {g['phantom_ready']} phantoms. "
        "Trust a workspace's verified domain; treat names as clues that need a colleague to corroborate them; drop "
        "guests and any workspace whose members already resolve to several companies. Synthetic data makes the "
        "guards look perfect; in production, audit a sample of attributions by hand each quarter.")
    out["caveat"] = ("Workspace metadata is personal context: use it only in aggregate at the account level, within "
                     "the permissions users granted, and never to contact an individual about a side project.")
    return out
