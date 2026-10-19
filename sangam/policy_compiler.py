"""Compile reward guidelines written in prose into the internal Policy.

The compiler is a Strands agent on Amazon Bedrock that returns a validated
`Policy` through structured output. Its instructions are the important part:
read the guidelines literally, never guess, turn every ambiguity into a plain
question for the policy owner, and record every default it fills in.

Without AWS credentials, `compile_guidelines` falls back to the reviewed
compilation stored next to an example document, and says so.

`grade_compile` checks a compilation against a reviewed one. It is how the
evals score the live compiler.
"""

from __future__ import annotations

import os
from pathlib import Path

from .policy import Policy

INSTRUCTIONS = """You turn a company's reward guidelines, written in plain language, into a structured reward
policy for an AI workspace product. People share agents, documents, spaces, embeds, digests and referral links;
the policy says which shares earn a reward and when.

Rules:
1. Read the guidelines literally. Do not improve the policy: if it pays for every share sent, say so.
2. Never guess. If a term could reasonably mean two different things that change who gets paid or when
   (for example "teammates", "partners", "meaningful use", "active"), leave the affected setting at its
   conservative default and add a plain question to open_questions, one per ambiguity.
3. Where the guidelines are silent, use these conservative defaults and add one plain sentence for each to
   defaults_applied: shares outside the company need an admin's OK; people who already have a license are not
   rewarded; no cap and no budget are invented (leave them empty).
4. "Same company" means the same work email domain. "Before a contract" means the sharer's company has no
   enterprise agreement yet; "after a contract" means it has one.
5. Write open questions and defaults for the policy owner, in ordinary words. Never mention field names,
   code, JSON or YAML."""


def compile_live(text: str) -> Policy:
    from strands import Agent
    from strands.models import BedrockModel
    model_id = os.environ.get("SANGAM_MODEL_ID")
    region = os.environ.get("AWS_REGION", "us-west-2")
    model = BedrockModel(model_id=model_id, region_name=region) if model_id else BedrockModel(region_name=region)
    agent = Agent(model=model, system_prompt=INSTRUCTIONS, callback_handler=None)
    return agent.structured_output(Policy, f"Compile these reward guidelines:\n\n{text}")


def _have_aws() -> bool:
    if os.environ.get("SANGAM_OFFLINE"):
        return False
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):      # Bedrock API key
        return True
    try:
        import boto3
        return boto3.Session().get_credentials() is not None
    except Exception:
        return False


def compile_guidelines(text: str, reviewed: str | Path | None = None) -> tuple[Policy, str]:
    """Returns (policy, how it was compiled)."""
    if _have_aws():
        return compile_live(text), "Compiled live by the policy agent."
    if reviewed and Path(reviewed).exists():
        return (Policy.model_validate_json(Path(reviewed).read_text(encoding="utf-8")),
                "Offline: showing the reviewed compilation of this document. Set AWS credentials with Bedrock "
                "access to compile it live.")
    raise RuntimeError("Compiling new guidelines needs AWS credentials with Amazon Bedrock access.")


def grade_compile(got: Policy, want: Policy) -> list[str]:
    """Plain-language differences that would change who gets paid or when. Empty means it passed.
    Wording of defaults and questions is not compared; the NUMBER of open questions must match
    within one, and a policy that should have questions must have at least one."""
    diffs = []
    if got.rewarded != want.rewarded:
        diffs.append(f"rewards the {got.rewarded}, should reward the {want.rewarded}")
    if got.reward_event != want.reward_event:
        diffs.append(f"pays on {got.reward_event}, should pay on {want.reward_event}")
    for stage in ("pre_contract", "post_contract"):
        g, w = set(getattr(got, stage)), set(getattr(want, stage))
        if g != w:
            diffs.append(f"{stage.replace('_', '-')} recipients {sorted(g)} should be {sorted(w)}")
    if set(got.loops) != set(want.loops):
        diffs.append(f"share kinds {sorted(got.loops)} should be {sorted(want.loops)}")
    for loop in set(got.loop_weights) | set(want.loop_weights):
        g, w = got.loop_weights.get(loop, 1.0), want.loop_weights.get(loop, 1.0)
        if (g > 1) != (w > 1) or (g < 1) != (w < 1):
            diffs.append(f"{loop} shares weighted {g}, should be weighted like {w}")
    for flag in ("pay_for_licensed_recipients", "require_admin_ok_external"):
        if getattr(got, flag) != getattr(want, flag):
            diffs.append(f"{flag.replace('_', ' ')} is {getattr(got, flag)}, should be {getattr(want, flag)}")
    if got.cap_per_user_per_month != want.cap_per_user_per_month:
        diffs.append(f"monthly cap {got.cap_per_user_per_month}, should be {want.cap_per_user_per_month}")
    if bool(want.open_questions) != bool(got.open_questions) or \
            abs(len(got.open_questions) - len(want.open_questions)) > 1:
        diffs.append(f"{len(got.open_questions)} open questions, expected about {len(want.open_questions)}")
    return diffs
