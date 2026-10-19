"""Reward guidelines in plain language.

People write reward guidelines as ordinary prose and approve a plain-English
policy card. The structured `Policy` below is internal plumbing: an agent
compiles prose into it (sangam/policy_compiler.py), and everything a person
sees is rendered back into sentences.

    prose guidelines --compile--> Policy --render--> policy card + warnings
                                         +--simulate--> outcome, in sentences

Three rules keep this honest:

  * The compiler never guesses. Anything the guidelines leave ambiguous becomes
    an open question, and a policy with open questions cannot be simulated or
    approved until a person answers them.
  * Anything the guidelines are silent on gets a conservative default, and the
    card says so ("The guidelines didn't say ...; we assumed ...").
  * How people respond to incentives (BEHAVIOR) is kept apart from what the
    policy says. Policy authors set policy; the behavioral assumptions are the
    growth team's, stated once, and tested with an A/B test.

Command line:

    python -m sangam.policy policies/examples/growth_team_q4.md
    python -m sangam.policy policies/examples/growth_team_q4.md --approve
"""

from __future__ import annotations

import hashlib
import re
import json
import sys
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from scipy.stats import poisson

from .dhruva import Dataset

Relation = Literal["same_company", "other_company", "personal"]
RewardEvent = Literal["none", "share_sent", "recipient_signup", "recipient_first_agent_action"]
LOOPS = ["agent", "asset", "space", "embed", "digest", "referral"]


class Policy(BaseModel):
    """Internal form of a reward policy. People never read or write this."""
    name: str = Field(description="Short name for the policy, taken from the guidelines' title if there is one.")
    reward_event: RewardEvent = Field(
        description="What earns the reward: the share being sent, the recipient signing up, or the recipient "
                    "completing their first agent action (activation). 'none' only for a no-reward baseline.")
    loops: list[Literal["agent", "asset", "space", "embed", "digest", "referral"]] = Field(
        default_factory=lambda: list(LOOPS),
        description="Which kinds of share count: agent (shared agent), asset (shared document, analysis or "
                    "dashboard URL), space (shared space or knowledge base), embed (Slack or email embed), "
                    "digest (recurring digest), referral (referral link).")
    loop_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Multipliers for share types the guidelines say should earn more or less; omit for 1.0.")
    pre_contract: list[Relation] = Field(
        default_factory=list,
        description="Before the sharer's company has a contract, which recipients count: same_company "
                    "(colleagues on the same work domain), other_company, personal (personal email addresses).")
    post_contract: list[Relation] = Field(
        default_factory=list,
        description="After the sharer's company has a contract, which recipients count.")
    pay_for_licensed_recipients: bool = Field(
        default=False,
        description="True only if the guidelines explicitly reward shares to people who already have a license.")
    require_admin_ok_external: bool = Field(
        default=True,
        description="Whether shares outside the company need a workspace admin's approval before they earn.")
    reward: str = Field(default="", description="What the reward is, in the guidelines' words (e.g. '$20 in "
                                                 "usage credits'). Empty if unstated.")
    cap_per_user_per_month: Optional[int] = Field(
        default=None, description="Most rewards one person can earn in a month; null if no cap is stated.")
    monthly_budget: str = Field(default="", description="Total budget in the guidelines' words; empty if unstated.")
    defaults_applied: list[str] = Field(
        default_factory=list,
        description="Plain sentences naming each thing the guidelines were silent on and the conservative "
                    "default used, e.g. 'The guidelines didn't say whether shares outside the company need an "
                    "admin's OK; we assumed they do.'")
    open_questions: list[str] = Field(
        default_factory=list,
        description="Plain questions for the policy owner about anything ambiguous, one per ambiguity. "
                    "Never guess an answer to these.")


# ---------- built-in policies (the arms of the viral-loops simulation) ----------

ALL = ["same_company", "other_company", "personal"]
WEIGHTS = {"agent": 1.6, "space": 1.4, "asset": 1.0, "digest": 0.6, "embed": 0.6, "referral": 1.0}
BUILTIN = {
    "no_reward": Policy(name="No reward (status quo)", reward_event="none"),
    "per_share_sent": Policy(name="Reward every share sent", reward_event="share_sent", pre_contract=ALL,
                             post_contract=ALL, pay_for_licensed_recipients=True, require_admin_ok_external=False),
    "per_signup": Policy(name="Reward each sign-up", reward_event="recipient_signup", pre_contract=ALL,
                         post_contract=ALL, pay_for_licensed_recipients=True, require_admin_ok_external=False),
    "per_activation": Policy(name="Reward each activation", reward_event="recipient_first_agent_action",
                             pre_contract=ALL, post_contract=ALL, pay_for_licensed_recipients=True,
                             require_admin_ok_external=False),
    "per_activation_weighted": Policy(name="Reward each activation, weighted by share type",
                                      reward_event="recipient_first_agent_action", loop_weights=WEIGHTS,
                                      pre_contract=ALL, post_contract=ALL, pay_for_licensed_recipients=True,
                                      require_admin_ok_external=False),
    "stage_aware": Policy(name="Stage-aware activation reward", reward_event="recipient_first_agent_action",
                          loop_weights=WEIGHTS, pre_contract=["same_company"], post_contract=["other_company"]),
}

# How people respond to each kind of incentive. These are the growth team's stated
# assumptions, not policy: extra sharing it causes (uplift), how good the extra shares
# are (quality), and whether recipients tune out (fatigue).
BEHAVIOR = {
    "none": {"uplift": 0.0, "quality": 1.0, "fatigue": 1.0, "note": "status quo"},
    "share_sent": {"uplift": 0.80, "quality": 0.25, "fatigue": 0.90,
                   "note": "people blast links for credit; recipients learn to ignore them"},
    "recipient_signup": {"uplift": 0.40, "quality": 0.45, "fatigue": 1.00,
                         "note": "sharers recruit people who sign up as a favor"},
    "recipient_first_agent_action": {"uplift": 0.25, "quality": 0.90, "fatigue": 1.00,
                                     "note": "sharers pick people who will actually use it"},
}
LICENSED_FIRST_ACTION = 0.5     # chance a licensed colleague's first agent action follows a share


# ---------- plain-English rendering ----------

_REL = {"same_company": "colleagues at their own company",
        "other_company": "people at other companies (customers, partners, study participants)",
        "personal": "personal email addresses"}
_LOOP = {"agent": "shared agents", "asset": "shared documents, analyses and dashboards",
         "space": "shared spaces and knowledge bases", "embed": "links embedded in Slack or email",
         "digest": "recurring digests", "referral": "referral links"}
_EVENT = {"share_sent": "when a share is sent, whether or not anyone opens it",
          "recipient_signup": "when the person they shared with signs up",
          "recipient_first_agent_action": "when the person they shared with completes their first agent action "
                                          "(not when the share is sent, and not at sign-up)"}


def _join(xs: list[str]) -> str:
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def fingerprint(p: Policy) -> str:
    return hashlib.sha256(p.model_dump_json().encode()).hexdigest()[:10]


def render_card(p: Policy) -> str:
    """The policy as a person reads and approves it. No field names, no code."""
    lines = [f"## {p.name}"]
    if p.reward_event == "none":
        return "\n\n".join(lines + ["Nobody earns a reward for sharing."])
    lines.append(f"**What earns a reward.** A person earns a reward {_EVENT[p.reward_event]}.")
    if p.reward:
        lines.append(f"**The reward.** {p.reward[0].upper() + p.reward[1:]}.")
    stage = []
    stages = (("Before their company has a contract", p.pre_contract),
              ("After their company has a contract", p.post_contract))
    if set(p.pre_contract) == set(p.post_contract):
        stages = (("Whether or not their company has a contract", p.pre_contract),)
    for label, rels in stages:
        rels = [r for r in ALL if r in rels]
        stage.append(f"{label}, shares to {_join([_REL[r] for r in rels])} count." if rels
                     else f"{label}, no shares earn a reward.")
    lines.append("**Which shares count.** " + " ".join(stage))
    if set(p.loops) == set(LOOPS):
        kinds = "Every kind of share counts"
    else:
        kinds = f"Only {_join([_LOOP[l] for l in LOOPS if l in p.loops])} count"
    more = [l for l in LOOPS if p.loop_weights.get(l, 1) > 1 and l in p.loops]
    less = [l for l in LOOPS if p.loop_weights.get(l, 1) < 1 and l in p.loops]
    if more:
        kinds += f"; {_join([_LOOP[l] for l in more])} earn more"
    if less:
        kinds += f"; {_join([_LOOP[l] for l in less])} earn less"
    lines.append(f"**Kinds of share.** {kinds}.")
    never = []
    if not p.pay_for_licensed_recipients:
        never.append("shares to people who already have a license")
    if never:
        lines.append(f"**Never rewarded.** {_join(never)[0].upper() + _join(never)[1:]}.")
    external = "other_company" in p.pre_contract + p.post_contract or "personal" in p.pre_contract + p.post_contract
    if external:
        lines.append("**Outside the company.** " + ("Shares outside the company earn only after a workspace admin "
                                                     "approves external sharing." if p.require_admin_ok_external
                                                     else "Shares outside the company earn without an admin's "
                                                          "approval."))
    limits = []
    limits.append(f"at most {p.cap_per_user_per_month} rewards per person per month"
                  if p.cap_per_user_per_month else "no limit per person")
    limits.append(f"a budget of {p.monthly_budget}" if p.monthly_budget else "no stated budget")
    lines.append(f"**Limits.** {_join(limits)[0].upper() + _join(limits)[1:]}.")
    if p.defaults_applied:
        lines += ["**Filled in where the guidelines were silent** (confirm or correct):"]
        lines += [f"- {d}" for d in p.defaults_applied]
    if p.open_questions:
        lines += ["**Questions to answer before this can be simulated or approved:**"]
        lines += [f"{i}. {q}" for i, q in enumerate(p.open_questions, 1)]
    text = "\n\n".join(lines).replace("\n\n- ", "\n- ")
    return re.sub(r"\n\n(\d+\. )", r"\n\1", text)


def lint(p: Policy) -> list[dict]:
    """Problems a policy owner should know about, in plain language."""
    out = []

    def add(id_, severity, text):
        out.append({"id": id_, "severity": severity, "text": text})

    if p.reward_event == "none":
        return out
    allrel = set(p.pre_contract) | set(p.post_contract)
    if p.reward_event == "share_sent":
        add("pays_on_share", "warning",
            "This pays for sending links, whether or not anyone uses them. People will send links to everyone "
            "they know, and recipients will learn to ignore them. Pay when the recipient completes their first "
            "agent action instead.")
    if p.reward_event == "recipient_signup":
        add("pays_on_signup", "warning",
            "This pays for sign-ups. Sharers recruit people who sign up as a favor and never use the product. "
            "Pay when the recipient completes their first agent action instead.")
    if p.pay_for_licensed_recipients:
        add("pays_licensed", "warning",
            "This pays when colleagues who already have a license use something shared with them. That usage "
            "is already paid for and would mostly happen anyway.")
    if "personal" in allrel:
        add("personal_email", "warning",
            "This rewards shares to personal email addresses, which anyone can collect by sharing with a second "
            "account of their own.")
    if p.cap_per_user_per_month is None:
        add("no_cap", "warning",
            "There is no limit on how many rewards one person can earn in a month, so a few people can drain "
            "the budget.")
    if ("other_company" in allrel or "personal" in allrel) and not p.require_admin_ok_external:
        add("external_no_admin", "warning",
            "Shares outside the company earn rewards without an admin's approval. Encouraging people to send "
            "company work outside the company needs the company's consent.")
    if "same_company" in p.post_contract:
        add("post_contract_colleagues", "caution",
            "After a contract, this rewards shares to unlicensed colleagues at the customer. Adding seats there "
            "is the account team's job; rewarding it may pay twice for the same expansion.")
    if "other_company" in p.pre_contract:
        add("pre_contract_external", "caution",
            "Before a contract, this rewards shares to other companies. That spreads early users thin instead "
            "of building one company toward the point where a sales conversation makes sense.")
    if not p.monthly_budget:
        add("no_budget", "caution", "No budget is stated, so finance cannot see the most this could cost.")
    return out


# ---------- simulation ----------

def _context(ds: Dataset, ready_rule: dict, outcomes: pd.DataFrame, data_dir="data") -> dict:
    from .loops import _ledger, expand_vs_land
    sh = _ledger(ds, data_dir)
    prospects = set(outcomes.account_id)
    u = ds.users[ds.users.channel == "self_serve"]
    act = u[u.activated_agent & u.account_id.isin(prospects)]
    g = sh.groupby(["loop", "relation", "stage", "recipient_licensed"])
    seg = pd.DataFrame({"n": g.size(), "signup": g.signed_up.mean(), "act": g.activated.mean(),
                        "view": g.viewed.mean()}).reset_index()
    land = expand_vs_land(ds, ready_rule, outcomes, data_dir)
    ext = sh[(sh.relation == "other_company") & sh.activated]
    sc = sh[(sh.relation == "same_company") & (sh.stage == "pre_contract") & sh.sender_account.isin(prospects)]
    return {"seg": seg, "k": ready_rule["min_activated"], "base_act": act.groupby("account_id").size(),
            "seed_rate": land.companies_seeded.sum() / max(len(ext), 1),
            "per_acct": sc.groupby(["sender_account", "loop"]).size().rename("n").reset_index()}


def _simulate_one(ctx: dict, p: Policy) -> dict:
    seg = ctx["seg"].copy()
    b = BEHAVIOR[p.reward_event]
    w = p.loop_weights
    if p.reward_event == "none":
        elig = np.zeros(len(seg), bool)
    else:
        pre = seg.relation.isin(p.pre_contract) & (seg.stage == "pre_contract")
        post = seg.relation.isin(p.post_contract) & (seg.stage == "post_contract")
        elig = ((pre | post) & seg.loop.isin(p.loops)
                & (p.pay_for_licensed_recipients | ~seg.recipient_licensed)).to_numpy()
    up = np.where(elig, b["uplift"] * seg.loop.map(lambda l: w.get(l, 1.0)), 0.0)
    fat, q = b["fatigue"], b["quality"]
    new_users = (~seg.recipient_licensed) * seg.n * (fat + up * q)
    lic_actions = seg.recipient_licensed * seg.n * (1 + up) * seg.view * LICENSED_FIRST_ACTION
    if p.reward_event == "none":
        paid = 0.0
    elif p.reward_event == "share_sent":
        paid = (seg.n * (1 + up) * elig).sum()
    elif p.reward_event == "recipient_signup":
        paid = (new_users * seg.signup * elig).sum()
    else:
        paid = ((new_users * seg.act + lic_actions * p.pay_for_licensed_recipients) * elig).sum()
    # expansion: extra same-company activated recipients at pre-contract prospects
    rate = seg[(seg.relation == "same_company") & (seg.stage == "pre_contract")].groupby("loop")[
        ["signup", "act"]].mean()
    pre_ok = "same_company" in p.pre_contract and p.reward_event != "none"
    upl = {l: (b["uplift"] * w.get(l, 1.0) if pre_ok and l in p.loops else 0.0) for l in rate.index}
    pa = ctx["per_acct"]
    extra = pa.assign(d=pa.n * pa.loop.map(lambda l: (fat - 1) + upl.get(l, 0) * q)
                      * pa.loop.map(rate.signup) * pa.loop.map(rate.act))
    delta = extra.groupby("sender_account").d.sum().clip(lower=0)
    need = (ctx["k"] - ctx["base_act"].reindex(delta.index).fillna(0)).clip(lower=0)
    crossed = round(float(poisson.sf(need[need > 0] - 1, delta[need > 0]).sum()), 1)
    # landing: extra activated external recipients from post-contract senders
    m = ((seg.stage == "post_contract") & (seg.relation == "other_company") & ~seg.recipient_licensed).to_numpy()
    post = seg[m]
    seeded = float((post.n * (fat - 1 + up[m] * q) * post.signup * post.act).sum() * ctx["seed_rate"])
    return {"shares": round(float((seg.n * (1 + up)).sum())), "signups": round(float((new_users * seg.signup).sum())),
            "activated_new_users": round(float((new_users * seg.act).sum())), "rewards_paid": round(float(paid)),
            "extra_prospects_over_trigger": crossed,
            "extra_companies_seeded_by_customers": round(seeded, 1), "assumption": b["note"]}


def _finish(r: dict, base: dict) -> dict:
    inc = r["activated_new_users"] - base["activated_new_users"]
    r["incremental_activated"] = round(inc)
    r["rewards_per_incremental_activated"] = round(r["rewards_paid"] / inc, 2) if inc > 0 else None
    return r


def simulate_builtins(ds: Dataset, ready_rule: dict, outcomes: pd.DataFrame, data_dir="data") -> dict:
    ctx = _context(ds, ready_rule, outcomes, data_dir)
    out = {k: _simulate_one(ctx, p) for k, p in BUILTIN.items()}
    if not BUILTIN["stage_aware"].pay_for_licensed_recipients:
        out["stage_aware"]["assumption"] = ("pre-contract: reward same-company shares; post-contract: reward "
                                            "external shares to non-customers; never pay for licensed colleagues")
    out["per_activation_weighted"]["assumption"] = "agent and space shares, which show the product working, earn more"
    return {k: _finish(v, out["no_reward"]) for k, v in out.items()}


class NotReady(Exception):
    pass


def simulate(p: Policy, ds: Dataset, ready_rule: dict, outcomes: pd.DataFrame, data_dir="data") -> dict:
    """Simulate a compiled policy next to the status quo and the reference stage-aware policy."""
    if p.open_questions:
        raise NotReady("This policy has open questions. Answer them in the guidelines and compile again.")
    ctx = _context(ds, ready_rule, outcomes, data_dir)
    base = _simulate_one(ctx, BUILTIN["no_reward"])
    return {"policy": _finish(_simulate_one(ctx, p), base),
            "reference": _finish(_simulate_one(ctx, BUILTIN["stage_aware"]), base),
            "status_quo": _finish(base, base)}


def describe(sim: dict) -> str:
    """Simulation results as sentences."""
    p, ref = sim["policy"], sim["reference"]
    if p["incremental_activated"] <= 0:
        head = "Compared with offering no reward, this policy adds no activated users."
    else:
        head = (f"Compared with offering no reward, this policy would add about {p['incremental_activated']:,} "
                f"activated users, push about {p['extra_prospects_over_trigger']} more prospect companies to the "
                f"point where a sales conversation makes sense, and help customers bring in about "
                f"{p['extra_companies_seeded_by_customers']} new companies. It would pay about "
                f"{p['rewards_paid']:,} rewards, or {p['rewards_per_incremental_activated']} per added "
                f"activated user.")
    same = all(p[k] == ref[k] for k in ("incremental_activated", "rewards_paid", "extra_prospects_over_trigger"))
    cmp_ = " This matches the stage-aware reference policy." if same else (f" For comparison, the stage-aware reference policy adds about {ref['incremental_activated']:,} "
            f"activated users and {ref['extra_prospects_over_trigger']} prospect companies for about "
            f"{ref['rewards_paid']:,} rewards ({ref['rewards_per_incremental_activated']} per added activated user).")
    tail = (" These figures rest on the growth team's assumptions about how people respond to incentives; "
            "confirm them with an A/B test, randomized by workspace, before rolling the policy out.")
    return head + cmp_ + tail


# ---------- review: the whole thing a person sees ----------

def review(p: Policy, ds: Dataset | None = None, ready_rule: dict | None = None,
           outcomes: pd.DataFrame | None = None) -> str:
    parts = [render_card(p)]
    issues = lint(p)
    if issues:
        parts += ["", "### Things to know"]
        parts += [f"- {'⚠️' if i['severity'] == 'warning' else 'ℹ️'} {i['text']}" for i in issues]
    parts += ["", "### What we expect it to do"]
    if p.open_questions:
        parts.append("Not simulated yet: answer the questions above first.")
    elif ds is not None:
        parts.append(describe(simulate(p, ds, ready_rule, outcomes)))
    return "\n".join(parts)


def examples(folder: str | Path = "policies/examples") -> dict:
    """Each example document with its card, warnings and expected outcome, for the report."""
    from .tools import _outcomes, _ready_accounts, dataset
    out = {}
    for doc in sorted(Path(folder).glob("*.md")):
        p = Policy.model_validate_json(doc.with_suffix(".reviewed.json").read_text())
        sim = None if p.open_questions else simulate(p, dataset(), _ready_accounts()[1], _outcomes())
        out[doc.stem] = {"path": str(doc), "title": p.name, "card": render_card(p), "issues": lint(p),
                         "open_questions": p.open_questions, "simulation": sim,
                         "outcome": describe(sim) if sim else None}
    return out


def approve(p: Policy, path: str | Path) -> Path:
    """Record a person's approval of the card they read. Refuses while questions are open."""
    if p.open_questions:
        raise NotReady("A policy with open questions cannot be approved.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_card(p) + f"\n\n_Approved card {fingerprint(p)}._\n")
    path.with_suffix(".policy.json").write_text(p.model_dump_json(indent=2))
    return path


def _main(argv: list[str]) -> int:
    from .policy_compiler import compile_guidelines
    from .tools import _outcomes, _ready_accounts, dataset
    if not argv:
        print(__doc__)
        return 1
    doc = Path(argv[0])
    p, how = compile_guidelines(doc.read_text(), reviewed=doc.with_suffix(".reviewed.json"))
    print(f"_{how}_\n")
    print(review(p, dataset(), _ready_accounts()[1], _outcomes()))
    if "--approve" in argv:
        try:
            out = approve(p, Path("policies/approved") / (doc.stem + ".md"))
            print(f"\nApproved. Card saved to {out}.")
        except NotReady as e:
            print(f"\nNot approved: {e}")
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
