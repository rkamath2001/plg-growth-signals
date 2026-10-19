"""The agent's tools. Each is a plain function over the Dhruva metric layer that
returns JSON-ready data, so the agent can only quote governed numbers, and the
same functions can be tested without a model."""

from __future__ import annotations

from functools import lru_cache

from . import cohorts
from .dhruva import METRIC_DEFINITIONS, MIN_COHORT, Dataset, load, retention_by
from .connectors import evaluate as _connector_eval
from .identity import resolution_summary
from .loops import summarize as _loops_summary
from .motions import (channel_ranking, conversion_by_activated, find_threshold, prospect_rollup,
                      provider_ranking, work_email_whatif)
from .pqa import account_rollup, score

import pandas as pd

DIMENSIONS = ["segment", "source", "provider", "function", "plan", "rollout_wave", "resolution"]


@lru_cache(maxsize=1)
def dataset(data_dir: str = "data") -> Dataset:
    return load(data_dir)


def metric_definitions() -> dict:
    return {"definitions": METRIC_DEFINITIONS, "min_cohort_size": MIN_COHORT}


def retention_by_dimension(dimension: str, week: int = 8, exclude_internal: bool = True) -> dict:
    if dimension not in DIMENSIONS:
        return {"error": f"Unknown dimension. Choose one of {DIMENSIONS}."}
    t = retention_by(dataset(), dimension, week, exclude_internal)
    return {"dimension": dimension, "week": week, "exclude_internal": exclude_internal,
            "rows": t.reset_index().rename(columns={"g": dimension}).to_dict("records")}


def headline_inflation() -> dict:
    return cohorts.headline_inflation(dataset())


def activation_test() -> dict:
    return cohorts.activation_test(dataset())


def connector_breadth() -> dict:
    return cohorts.connector_breadth(dataset())


def check_feature_lift(feature: str = "desktop") -> dict:
    allowed = ["desktop", "upgraded"]
    if feature not in allowed:
        return {"error": f"Feature must be one of {allowed}."}
    return cohorts.simpson_check(dataset(), feature)


def identity_resolution() -> dict:
    t = resolution_summary(dataset().users)
    return {"by_provider": t.reset_index().to_dict("records"),
            "note": "Personal domains and Apple private-relay addresses cannot be tied to a company."}


def product_qualified_accounts(n: int = 10, include_customers: bool = False) -> dict:
    s = score(account_rollup(dataset()))
    if not include_customers:
        s = s[~s.is_customer]
    noise = s[s.noise_flag]
    return {
        "top": s.head(n).reset_index()[["account_id", "company", "score", "play", "reasons"]].to_dict("records"),
        "noise_accounts_suppressed": noise.reset_index()[["account_id", "company", "reasons"]].head(5).to_dict("records"),
        "n_noise_flagged": int(noise.shape[0]),
    }


@lru_cache(maxsize=1)
def _outcomes(data_dir: str = "data") -> pd.DataFrame:
    return pd.read_csv(f"{data_dir}/account_outcomes.csv")


def sales_trigger_threshold() -> dict:
    r = prospect_rollup(dataset(), _outcomes())
    res = find_threshold(r)
    res["conversion_by_activated_users"] = (conversion_by_activated(r).rename_axis("index").reset_index()
                                            .rename(columns={"index": "activated_users"}).to_dict("records"))
    return res


def acquisition_channel_ranking() -> dict:
    r = prospect_rollup(dataset(), _outcomes())
    rule = find_threshold(r)["recommended_rule"]
    ready = set(r[(r.activated >= rule["min_activated"]) & (r.functions >= rule["min_functions"])].index)
    return channel_ranking(dataset(), ready, _outcomes())


def _ready_accounts() -> tuple[set[str], dict]:
    r = prospect_rollup(dataset(), _outcomes())
    rule = find_threshold(r)["recommended_rule"]
    return set(r[(r.activated >= rule["min_activated"]) & (r.functions >= rule["min_functions"])].index), rule


def signin_provider_ranking() -> dict:
    return provider_ranking(dataset(), _ready_accounts()[0])


def work_email_prompt_whatif(uptake: float = 0.3) -> dict:
    truth = pd.read_csv("data/ground_truth/users_truth.csv")
    return work_email_whatif(dataset(), truth, _outcomes(), _ready_accounts()[1], uptake)


def connector_identity() -> dict:
    truth = pd.read_csv("data/ground_truth/users_truth.csv")
    return _connector_eval(dataset(), truth, _outcomes(), _ready_accounts()[1])


def viral_loops() -> dict:
    out = _loops_summary(dataset(), _ready_accounts()[1], _outcomes())
    return out


ALL_TOOLS = [metric_definitions, retention_by_dimension, headline_inflation, activation_test,
             connector_breadth, check_feature_lift, identity_resolution, product_qualified_accounts,
             sales_trigger_threshold, acquisition_channel_ranking, signin_provider_ranking,
             connector_identity, viral_loops]
