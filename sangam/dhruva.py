"""Dhruva: the governed metric layer.

Dhruva is the pole star in Hindu tradition, the fixed point you navigate by.
Every number in Sangam, whether computed by a notebook or quoted by the agent,
comes from the definitions in this module, so "active user" means the same
thing in every answer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .generate import OBSERVE_WEEKS
from .identity import resolve

METRIC_DEFINITIONS = {
    "active_week": "A week in which the user asked at least one question or completed at least one agent action.",
    "retained_wN": "The user was active in the Nth week after signup (signup week = week 0).",
    "activated_agent": "The user completed at least one agent action in their signup week.",
    "activated_question_only": "The user asked a question in their signup week but completed no agent action.",
    "connectors_w0": "Number of app connectors linked in the signup week.",
    "north_star": "Weekly agent-active users: users completing at least one agent action in the week, external users only.",
    "segment": "internal = customer-zero deployment; enterprise_external = directory users at paying customers; self_serve = personal sign-ups.",
}

MIN_COHORT = 150  # smaller cohorts are reported but flagged as too small to act on


@dataclass
class Dataset:
    accounts: pd.DataFrame
    users: pd.DataFrame          # resolved, with per-user features
    events: pd.DataFrame
    activity: pd.DataFrame       # user x relative-week active flags (0/1)


def load(data_dir: str | Path = "data") -> Dataset:
    d = Path(data_dir)
    accounts = pd.read_csv(d / "accounts.csv")
    users = pd.read_csv(d / "users.csv")
    events = pd.read_csv(d / "events.csv.gz")
    users = resolve(users, accounts)

    internal_ids = set(accounts.loc[accounts.company.str.contains("(internal)", regex=False), "account_id"])
    users["segment"] = np.where(
        users.account_id.isin(internal_ids), "internal",
        np.where(users.channel == "enterprise", "enterprise_external", "self_serve"))

    ev = events.merge(users[["user_id", "signup_week"]], on="user_id")
    ev["rel_week"] = ev.week - ev.signup_week
    w0 = ev[ev.rel_week == 0].pivot_table(index="user_id", columns="event_type",
                                          values="count", aggfunc="sum", fill_value=0)
    feats = pd.DataFrame(index=users.user_id)
    for col in ["agent_action", "question_asked", "connector_linked", "agent_shared",
                "teammate_invited", "desktop_installed"]:
        feats[col + "_w0"] = w0.get(col, pd.Series(dtype=float)).reindex(feats.index).fillna(0).astype(int)
    feats["activated_agent"] = feats.agent_action_w0 > 0
    feats["activated_question_only"] = (feats.question_asked_w0 > 0) & ~feats.activated_agent
    feats["connectors_w0"] = feats.connector_linked_w0
    feats["desktop"] = feats.desktop_installed_w0 > 0
    upgraded = set(events.loc[events.event_type == "plan_upgraded", "user_id"])
    feats["upgraded"] = feats.index.isin(upgraded)

    act = ev[ev.event_type.isin(["question_asked", "agent_action"])]
    activity = (act.assign(v=1).pivot_table(index="user_id", columns="rel_week", values="v",
                                            aggfunc="max", fill_value=0)
                .reindex(index=users.user_id, columns=range(OBSERVE_WEEKS), fill_value=0))
    # weeks beyond the observation window are unknown, not inactive
    max_rel = OBSERVE_WEEKS - 1 - users.set_index("user_id").signup_week
    for w in activity.columns:
        activity.loc[max_rel < w, w] = np.nan

    users = users.merge(feats, left_on="user_id", right_index=True)
    return Dataset(accounts, users, events, activity)


def retention_curve(ds: Dataset, mask: pd.Series | None = None, weeks: int = 8) -> pd.Series:
    ids = ds.users.user_id if mask is None else ds.users.loc[mask, "user_id"]
    return ds.activity.loc[ids, list(range(1, weeks + 1))].mean().rename_axis("week")


def retention_at(ds: Dataset, week: int, mask: pd.Series | None = None) -> tuple[float, int]:
    ids = ds.users.user_id if mask is None else ds.users.loc[mask, "user_id"]
    col = ds.activity.loc[ids, week].dropna()
    return float(col.mean()), int(col.size)


def retention_by(ds: Dataset, dimension: str, week: int = 8,
                 exclude_internal: bool = True) -> pd.DataFrame:
    u = ds.users if not exclude_internal else ds.users[ds.users.segment != "internal"]
    r = ds.activity.loc[u.user_id, week]
    t = (pd.DataFrame({"g": u[dimension].to_numpy(), "r": r.to_numpy()})
         .dropna().groupby("g").r.agg(["mean", "size"]))
    t.columns = [f"w{week}_retention", "n"]
    t["too_small"] = t.n < MIN_COHORT
    return t.sort_values(f"w{week}_retention", ascending=False).round(3)


def north_star(ds: Dataset) -> pd.Series:
    ext = ds.users.loc[ds.users.segment != "internal", "user_id"]
    e = ds.events[(ds.events.event_type == "agent_action") & ds.events.user_id.isin(ext)]
    return e.groupby("week").user_id.nunique().rename("weekly_agent_active_users")
