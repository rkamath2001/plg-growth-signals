"""Growth analyst agent, built with Strands Agents on Amazon Bedrock.

The agent answers growth questions only through the governed tools in
`sangam/tools.py`. It must state sample sizes, separate signal from noise, and
name the most likely alternative explanation before recommending anything.

Run:  python -m sangam.agent "Which accounts should sales call this week, and why?"
Needs AWS credentials with Amazon Bedrock model access. Set SANGAM_MODEL_ID to
choose a model; otherwise the Strands default Bedrock model is used.
"""

from __future__ import annotations

import json
import os
import sys

from strands import Agent, tool
from strands.models import BedrockModel

from . import tools as T

SYSTEM_PROMPT = """You are a growth analyst for an AI workspace product. Answer only from the
tools; never estimate a number yourself. For every finding:
1. Quote the number and its sample size (n). If n is below the minimum cohort size, say it is too small to act on.
2. Report external users separately from the internal customer-zero deployment, whose use is mandated.
3. Before claiming a feature drives retention, check it within segments; if the lift disappears, say it is confounded.
4. Separate signal from noise: name the most likely alternative explanation and your confidence (high, medium, low).
5. End with one recommended action and the experiment that would confirm it.
Observational findings are hypotheses, not proof. Keep answers under 250 words."""


@tool
def metric_definitions() -> str:
    """Governed definitions of every metric and the minimum cohort size."""
    return json.dumps(T.metric_definitions())


@tool
def retention_by_dimension(dimension: str, week: int = 8, exclude_internal: bool = True) -> str:
    """Week-N retention grouped by a dimension: segment, source, provider, function, plan, rollout_wave or resolution."""
    return json.dumps(T.retention_by_dimension(dimension, week, exclude_internal), default=str)


@tool
def headline_inflation() -> str:
    """How much the internal customer-zero deployment inflates headline retention."""
    return json.dumps(T.headline_inflation(), default=str)


@tool
def activation_test() -> str:
    """Compares week-8 retention for users whose first week included an agent action vs only questions."""
    return json.dumps(T.activation_test(), default=str)


@tool
def connector_breadth() -> str:
    """Week-8 retention by number of app connectors linked in the signup week."""
    return json.dumps(T.connector_breadth(), default=str)


@tool
def check_feature_lift(feature: str = "desktop") -> str:
    """Checks whether a feature's retention lift holds within segments (Simpson's paradox check). Features: desktop, upgraded."""
    return json.dumps(T.check_feature_lift(feature), default=str)


@tool
def identity_resolution() -> str:
    """Share of self-serve users that can be tied to a company, by sign-in provider."""
    return json.dumps(T.identity_resolution(), default=str)


@tool
def product_qualified_accounts(n: int = 10, include_customers: bool = False) -> str:
    """Top product-qualified accounts with scores, reasons and recommended plays; also lists suppressed noise accounts."""
    return json.dumps(T.product_qualified_accounts(n, include_customers), default=str)


@tool
def sales_trigger_threshold() -> str:
    """Learns from observed contract outcomes how many activated independent users (and functions) a company needs before an enterprise sales motion pays off; compares with a sign-up-count rule."""
    return json.dumps(T.sales_trigger_threshold(), default=str)


@tool
def acquisition_channel_ranking() -> str:
    """Ranks self-serve acquisition channels (teammate invite, LinkedIn, search, YouTube, X, Reddit, direct, webinar) by volume, week-8 retention and sales-ready accounts per 1,000 sign-ups."""
    return json.dumps(T.acquisition_channel_ranking(), default=str)


def build_agent() -> Agent:
    model_id = os.environ.get("SANGAM_MODEL_ID")
    region = os.environ.get("AWS_REGION", "us-west-2")
    model = BedrockModel(model_id=model_id, region_name=region) if model_id else BedrockModel(region_name=region)
    return Agent(model=model, system_prompt=SYSTEM_PROMPT, callback_handler=None,
                 tools=[metric_definitions, retention_by_dimension, headline_inflation,
                        activation_test, connector_breadth, check_feature_lift,
                        identity_resolution, product_qualified_accounts,
                        sales_trigger_threshold, acquisition_channel_ranking])


def ask(question: str) -> str:
    return str(build_agent()(question))


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "What should we treat as activation, and how confident are you?"
    print(ask(q))
