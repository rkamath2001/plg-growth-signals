"""Synthetic data generator for Sangam.

Everything this module produces is SYNTHETIC. Company names, domains, users and
events are invented. The product modeled here is a generic "AI workspace"
(an assistant that answers questions, takes agent actions and connects to apps),
described from public information only. Nothing here reflects any company's
internal data.

The generator builds in known effects, recorded as expected results, so the analysis and the
agent can be graded against answers we know in advance:

  1. Activation: completing a first *agent action* in week 1 drives retention;
     asking a first *question* alone helps far less.
  2. Breadth: linking 3+ connectors in week 1 drives retention.
  3. Customer zero: a large internal deployment with mandated use retains far
     better than the market, inflating any headline that includes it.
  4. Simpson's trap: the desktop app looks like it lifts retention in aggregate,
     but it has no effect within any segment. The internal rollout installed it
     by default.
  5. Product-qualified accounts: a set of non-customer companies have clusters
     of independent self-serve adopters across several functions (real signal).
     A different set has signup spikes from a one-off webinar with almost no
     activation (noise that looks like signal).
  6. Unresolvable identities: personal email domains and private-relay
     addresses cannot be tied to a company.
  7. Channels: invited users carry the most intent, then LinkedIn and search;
     X and Reddit bring volume with low intent and mostly personal addresses.
  8. Sign-in providers: Google Workspace, Microsoft work accounts and work email carry company identity;
     employees signing in with Amazon or GitHub often use a personal address,
     and Apple's private relay hides it, so their companies are invisible.
  9. Connector identity: employees connect their employer's Slack, Teams or
     Jira, but also school and side-project workspaces (a robotics team Slack),
     big open communities, workspaces whose names collide with a company, and
     clients' workspaces as guests. Each is a false-positive trap.
 10. Viral loops: users share agents, assets, spaces, embeds, digests and
     referrals. Agent shares convert and activate best; asset shares reach
     other companies most; space invites retain best; embeds and digests are
     high-volume, low-conversion; referral sign-ups rarely activate.
 11. Sales trigger: a prospect's chance of signing a contract jumps once it
     has 5+ activated independent users, and again at 3+ functions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

START_DATE = pd.Timestamp("2026-03-02")  # a Monday; week 0
SIGNUP_WEEKS = 19                         # self-serve users sign up in weeks 0..18
ROLLOUT_WEEKS = 19                        # enterprise pilots start through week 14 and expand by week 18
WEEKLY_GROWTH = 1.04                      # self-serve sign-ups grow about 4% a week
OBSERVE_WEEKS = 20                        # activity observed through week 19

INDUSTRIES = ["financial services", "retail", "healthcare", "manufacturing",
              "media", "public sector", "technology", "consumer goods"]
FUNCTIONS = ["sales", "marketing", "finance", "operations", "engineering", "hr"]
# Acquisition channel for self-serve sign-ups (last-touch attribution).
SOURCES = ["teammate_invite", "linkedin", "search", "youtube", "x", "reddit", "direct"]
SOURCE_MIX = {  # who arrives through which channel
    "personal":  [0.06, 0.08, 0.20, 0.16, 0.18, 0.20, 0.12],
    "corporate": [0.18, 0.24, 0.22, 0.10, 0.08, 0.06, 0.12],
    "hot":       [0.40, 0.25, 0.15, 0.05, 0.05, 0.02, 0.08],
}
SOURCE_INTENT = {"teammate_invite": 0.6, "linkedin": 0.25, "search": 0.15, "direct": 0.05,
                 "youtube": 0.0, "x": -0.25, "reddit": -0.35, "webinar": 0.0}

# Viral loops. Each existing user may share; recipients who sign up become users
# whose source is the loop. Parameters are the generator's expected results.
#   rate      shares per sender over the window (scaled by activation and intent)
#   rel       recipient relation mix: same company / another company / personal
#   view, signup   per-share probabilities; delay = days from share to sign-up
#   intent    added to the recipient's intent (drives activation and retention)
LOOPS = {
    "agent":    dict(rate=0.25, act_mult=2.5, rel=[.80, .10, .10], view=.80, signup=.45, delay=(1, 4),   intent=0.8),
    "asset":    dict(rate=0.50, act_mult=1.6, rel=[.35, .55, .10], view=.70, signup=.25, delay=(2, 8),   intent=0.35),
    "space":    dict(rate=0.18, act_mult=1.8, rel=[.85, .10, .05], view=.85, signup=.50, delay=(3, 11),  intent=1.1),
    "embed":    dict(rate=1.20, act_mult=1.2, rel=[.80, .15, .05], view=.30, signup=.05, delay=(5, 21),  intent=0.1),
    "digest":   dict(rate=0.60, act_mult=1.3, rel=[.50, .40, .10], view=.50, signup=.06, delay=(7, 29),  intent=0.0),
    "referral": dict(rate=0.15, act_mult=1.0, rel=[.20, .20, .60], view=.65, signup=.35, delay=(1, 6),   intent=-0.5),
}
# Licensed enterprise users share more externally (clients, partners).
ENTERPRISE_REL = {"asset": [.25, .65, .10], "digest": [.40, .50, .10]}
SOURCE_INTENT.update({f"shared_{k}": v["intent"] for k, v in LOOPS.items()})
# Sign-in provider: work identities arrive mostly via Google Workspace, Microsoft
# work accounts or work email; consumer identities skew to Apple and Amazon.
PROVIDERS = ["google", "email", "apple", "github", "amazon", "microsoft"]
PROVIDER_MIX = {
    "personal":  [0.38, 0.14, 0.21, 0.10, 0.12, 0.05],
    "corporate": [0.44, 0.22, 0.07, 0.11, 0.02, 0.14],
}
PROVIDER_INTENT = {"microsoft": 0.0, "github": 0.15, "google": 0.05, "email": 0.0, "apple": -0.10, "amazon": -0.20}
# Employees who sign in with a consumer account often use a personal address,
# so their company is invisible even though they work there.
PERSONAL_ADDRESS_P = {"microsoft": 0.15, "amazon": 0.7, "github": 0.4, "google": 0.0, "email": 0.0, "apple": 0.0}
PERSONAL_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "icloud.com", "proton.me"]
RELAY_DOMAIN = "privaterelay.appleid.com"

_SYL_A = ["ar", "bel", "cor", "dun", "el", "fen", "gar", "hal", "ist", "jor",
          "kel", "lum", "mar", "nor", "ost", "pel", "quin", "ros", "sal", "tor",
          "ul", "ver", "wil", "yar", "zen"]
_SYL_B = ["by", "dale", "ford", "gate", "holm", "ia", "ley", "mont", "nex",
          "ora", "port", "ridge", "ton", "vale", "wick", "worth"]
_SUFFIX = ["Group", "Holdings", "Labs", "Partners", "Systems", "Co", "Industries",
           "Health", "Retail", "Financial", "Media", "Works"]


@dataclass
class Config:
    seed: int = 7
    n_accounts: int = 900
    n_contract_accounts: int = 60
    n_hot_pqa: int = 30          # true product-qualified accounts (signal)
    n_webinar_noise: int = 12    # signup spikes with no activation (noise)
    n_selfserve_background: int = 13000
    internal_seats: int = 3500


def _company_names(rng: np.random.Generator, n: int) -> list[str]:
    # 25 x 16 stems x 12 suffixes = 4,800 combinations; draw n distinct ones.
    combos = [(a, b, s) for a in _SYL_A for b in _SYL_B for s in _SUFFIX]
    pick = rng.choice(len(combos), size=n, replace=False)
    return [f"{(combos[i][0] + combos[i][1]).capitalize()} {combos[i][2]}" for i in pick]


def _domain(name: str) -> str:
    return name.lower().replace(" ", "") + ".example"


def _accounts(rng: np.random.Generator, cfg: Config) -> pd.DataFrame:
    names = _company_names(rng, cfg.n_accounts)
    df = pd.DataFrame({
        "account_id": [f"A{i:04d}" for i in range(cfg.n_accounts)],
        "company": names,
        "domain": [_domain(n) for n in names],
        "industry": rng.choice(INDUSTRIES, cfg.n_accounts),
        "size_band": rng.choice(["smb", "mid-market", "enterprise"], cfg.n_accounts,
                                p=[0.45, 0.35, 0.20]),
        # existing cloud customer with an assigned account team
        "has_account_team": rng.random(cfg.n_accounts) < 0.40,
    })
    df["segment"] = "prospect"
    df.loc[: cfg.n_contract_accounts - 1, "segment"] = "contract"
    hot = slice(cfg.n_contract_accounts, cfg.n_contract_accounts + cfg.n_hot_pqa)
    df.loc[df.index[hot], "segment"] = "prospect_hot"
    noise_start = cfg.n_contract_accounts + cfg.n_hot_pqa
    noise = slice(noise_start, noise_start + cfg.n_webinar_noise)
    df.loc[df.index[noise], "segment"] = "prospect_webinar"
    # contract accounts skew larger
    df.loc[df.segment == "contract", "size_band"] = rng.choice(
        ["mid-market", "enterprise"], cfg.n_contract_accounts, p=[0.4, 0.6])
    internal = pd.DataFrame([{
        "account_id": "A9999", "company": "Customer Zero (internal)",
        "domain": "customerzero.example", "industry": "technology",
        "size_band": "enterprise", "has_account_team": False, "segment": "internal",
    }])
    return pd.concat([df, internal], ignore_index=True)


def _user_rows(rng, n, *, channel, provider, account_id, domain, function,
               signup_week, plan, wave=None, source="sales_led"):
    return pd.DataFrame({
        "channel": channel, "source": source, "provider": provider, "account_id_truth": account_id,
        "email_domain": domain, "function": function, "signup_week": signup_week,
        "plan": plan, "rollout_wave": wave,
    }, index=range(n))


def _users(rng: np.random.Generator, cfg: Config, accounts: pd.DataFrame) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []

    # Enterprise rollouts: contract accounts, pilot wave then expansion wave.
    for _, acc in accounts[accounts.segment == "contract"].iterrows():
        seats = int(rng.integers(40, 400))
        pilot_week = int(rng.integers(0, 15))
        pilot_n = max(10, seats // 4)
        wave = np.where(np.arange(seats) < pilot_n, 1, 2)
        week = np.where(wave == 1, pilot_week,
                        np.minimum(pilot_week + rng.integers(4, 8), ROLLOUT_WEEKS - 1))
        parts.append(_user_rows(
            rng, seats, channel="enterprise", provider="sso",
            account_id=acc.account_id, domain=acc.domain,
            function=rng.choice(FUNCTIONS, seats), signup_week=week,
            plan="enterprise", wave=wave))

    # Customer zero: one big internal rollout with mandated use.
    n = cfg.internal_seats
    parts.append(_user_rows(
        rng, n, channel="enterprise", provider="sso", account_id="A9999",
        domain="customerzero.example", function=rng.choice(FUNCTIONS, n),
        signup_week=rng.integers(0, 4, n), plan="enterprise",
        wave=np.where(rng.random(n) < 0.3, 1, 2), source="internal_rollout"))

    w = WEEKLY_GROWTH ** np.arange(SIGNUP_WEEKS)
    week_p = w / w.sum()

    def weeks(n):
        return rng.choice(SIGNUP_WEEKS, n, p=week_p)

    def mix(kind, n):
        return rng.choice(SOURCES, n, p=SOURCE_MIX[kind])

    def selfserve(n, account_ids, domains, functions, weeks, source, kind="corporate"):
        kinds = np.broadcast_to(np.asarray(kind, dtype=object), (n,))
        provider = np.where(kinds == "personal",
                            rng.choice(PROVIDERS, n, p=PROVIDER_MIX["personal"]),
                            rng.choice(PROVIDERS, n, p=PROVIDER_MIX["corporate"]))
        dom = np.array(domains, dtype=object)
        # Employees on consumer sign-ins: company is real but the address is personal.
        hide = (kinds != "personal") & (rng.random(n) < pd.Series(provider).map(PERSONAL_ADDRESS_P).to_numpy())
        dom[hide] = rng.choice(PERSONAL_DOMAINS, int(hide.sum()))
        # Apple users often hide their address behind a private relay.
        relay = (provider == "apple") & (rng.random(n) < 0.6)
        dom[relay] = RELAY_DOMAIN
        acct = np.array(account_ids, dtype=object)
        return _user_rows(
            rng, n, channel="self_serve", provider=provider, account_id=acct,
            domain=dom, function=functions, signup_week=weeks,
            plan=np.where(rng.random(n) < 0.18, "plus", "free"), source=source)

    # Background self-serve: mostly personal domains, some shadow adoption at
    # ordinary prospects and at contract customers.
    n = cfg.n_selfserve_background
    kind = rng.choice(["personal", "prospect", "contract"], n, p=[0.62, 0.30, 0.08])
    plain = accounts[accounts.segment == "prospect"]
    contract = accounts[accounts.segment == "contract"]
    acct_ids = np.full(n, None, dtype=object)
    doms = rng.choice(PERSONAL_DOMAINS, n).astype(object)
    for k, pool in (("prospect", plain), ("contract", contract)):
        idx = np.flatnonzero(kind == k)
        pick = pool.iloc[rng.integers(0, len(pool), len(idx))]
        acct_ids[idx] = pick.account_id.to_numpy()
        doms[idx] = pick.domain.to_numpy()
    src = np.where(kind == "personal", mix("personal", n), mix("corporate", n))
    parts.append(selfserve(n, acct_ids, doms, rng.choice(FUNCTIONS, n),
                           weeks(n), src,
                           np.where(kind == "personal", "personal", "corporate")))

    # Hot PQAs: clusters of independent adopters across 3+ functions.
    for _, acc in accounts[accounts.segment == "prospect_hot"].iterrows():
        k = int(rng.integers(8, 26))
        fns = rng.choice(FUNCTIONS, k)
        fns[:3] = rng.choice(FUNCTIONS, 3, replace=False)  # guarantee breadth
        parts.append(selfserve(k, [acc.account_id] * k, [acc.domain] * k, fns,
                               weeks(k), mix("hot", k)))

    # Webinar noise: a burst of signups in a single week, one function.
    for _, acc in accounts[accounts.segment == "prospect_webinar"].iterrows():
        k = int(rng.integers(15, 35))
        week = int(rng.integers(2, SIGNUP_WEEKS))
        parts.append(selfserve(k, [acc.account_id] * k, [acc.domain] * k,
                               np.array(["marketing"] * k), np.full(k, week),
                               np.array(["webinar"] * k)))

    users = pd.concat(parts, ignore_index=True)
    users.insert(0, "user_id", [f"U{i:06d}" for i in range(len(users))])
    users["rollout_wave"] = users["rollout_wave"].astype("Int64")
    users["signup_date"] = START_DATE + pd.to_timedelta(users.signup_week * 7, unit="D")
    return users


def _behavior(rng: np.random.Generator, users: pd.DataFrame,
              accounts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    seg = users.account_id_truth.map(accounts.set_index("account_id").segment).fillna("personal")
    n = len(users)
    internal = (seg == "internal").to_numpy()
    enterprise = (users.channel == "enterprise").to_numpy()
    hot = (seg == "prospect_hot").to_numpy()
    webinar = (seg == "prospect_webinar").to_numpy()

    # Latent intent: hot clusters are engaged, webinar bursts are not.
    intent = (rng.normal(0, 1, n) + 0.9 * hot - 1.6 * webinar + 0.3 * enterprise
              + users.source.map(SOURCE_INTENT).fillna(0).to_numpy()
              + users.provider.map(PROVIDER_INTENT).fillna(0).to_numpy())

    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    asked_q = rng.random(n) < sigmoid(1.6 + 0.8 * intent)
    agent_action = rng.random(n) < sigmoid(-0.6 + 1.1 * intent + 0.8 * internal)
    connectors = np.clip(rng.poisson(np.exp(0.2 + 0.45 * intent + 0.4 * enterprise)), 0, 8)
    invited = rng.random(n) < sigmoid(-2.2 + 0.9 * intent + 0.9 * hot)
    shared = rng.random(n) < sigmoid(-2.4 + 0.9 * intent + 1.2 * hot)
    # Desktop app: installed by default for customer zero; NO causal effect below.
    desktop = rng.random(n) < np.where(internal, 0.90, np.where(enterprise, 0.30, 0.15))

    # Weekly survival probability. Configured causal effects only.
    logit_s = (0.6 + 1.1 * agent_action + 0.25 * (asked_q & ~agent_action)
               + 0.7 * (connectors >= 3) + 0.4 * shared + 0.25 * intent
               + 0.4 * enterprise + 2.2 * internal - 1.0 * webinar)
    survive = sigmoid(logit_s)

    uid = users.user_id.to_numpy()
    start = users.signup_week.to_numpy()
    frames = []

    def add(mask, week, event_type, count):
        mask = np.asarray(mask, dtype=bool)
        count = np.broadcast_to(np.asarray(count), mask.shape)
        week = np.broadcast_to(np.asarray(week), mask.shape)
        frames.append(pd.DataFrame({"user_id": uid[mask], "week": week[mask],
                                    "event_type": event_type, "count": count[mask]}))

    # First-week behavior.
    ones = np.ones(n, dtype=int)
    add(ones, start, "signup", 1)
    add(desktop, start, "desktop_installed", 1)
    add(asked_q, start, "question_asked", rng.integers(1, 6, n))
    add(agent_action, start, "agent_action", rng.integers(1, 4, n))
    add(connectors > 0, start, "connector_linked", connectors)
    add(shared, start, "agent_shared", 1)
    add(invited, start, "teammate_invited", rng.integers(1, 4, n))

    # Later weeks: survive each week with probability `survive`, then be active
    # in a surviving week with probability 0.88.
    rel = np.arange(1, OBSERVE_WEEKS)                      # weeks after signup
    alive = np.cumprod(rng.random((n, rel.size)) < survive[:, None], axis=1).astype(bool)
    abs_week = start[:, None] + rel[None, :]
    active = alive & (abs_week < OBSERVE_WEEKS) & (rng.random((n, rel.size)) < 0.88)
    r_idx, c_idx = np.nonzero(active)
    wk = abs_week[r_idx, c_idx]
    q = rng.poisson(3 + 2 * asked_q[r_idx])
    a = rng.poisson(0.5 + 1.8 * agent_action[r_idx])
    s = rng.random(r_idx.size) < (0.05 + 0.1 * shared[r_idx])
    for mask, et, cnt in ((q > 0, "question_asked", q), (a > 0, "agent_action", a),
                          (s, "agent_shared", 1)):
        cnt = np.broadcast_to(np.asarray(cnt), mask.shape)
        frames.append(pd.DataFrame({"user_id": uid[r_idx[mask]], "week": wk[mask],
                                    "event_type": et, "count": cnt[mask]}))
    events = pd.concat(frames, ignore_index=True)

    # Plus upgrades among self-serve users who stayed.
    upgrades = users.loc[(users.channel == "self_serve") & (users.plan == "free")]
    up = upgrades.sample(frac=0.08, random_state=rng)
    events = pd.concat([events, pd.DataFrame({
        "user_id": up.user_id, "week": np.minimum(up.signup_week + 2, OBSERVE_WEEKS - 1),
        "event_type": "plan_upgraded", "count": 1})], ignore_index=True)

    truth = pd.DataFrame({"user_id": users.user_id, "intent": intent.round(3),
                          "weekly_survival": survive.round(3), "agent_action_w0": agent_action})
    return events, truth


# Configured sales-trigger threshold: conversion jumps once an account has this many
# activated independent users, and again once they span 3+ functions.
THRESHOLD_ACTIVATED = 5
THRESHOLD_FUNCTIONS = 3


def _loops(rng, users, truth, accounts) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Shares by existing users, and the recipients who sign up because of them."""
    seg = accounts.set_index("account_id").segment
    dom = accounts.set_index("account_id").domain
    t = truth.set_index("user_id")
    snd = users[users.account_id_truth.map(seg).fillna("personal") != "internal"].copy()
    snd["activated"] = snd.user_id.map(t.agent_action_w0).to_numpy()
    snd["intent"] = snd.user_id.map(t.intent).to_numpy()
    snd["licensed"] = snd.account_id_truth.map(seg).eq("contract").to_numpy()
    others = accounts[accounts.segment.isin(["prospect", "prospect_hot", "contract"])].account_id.to_numpy()
    rows = []
    for loop, cfg in LOOPS.items():
        if loop == "referral":
            senders = snd[snd.channel == "self_serve"]
        else:
            senders = snd
        lam = (cfg["rate"] * np.where(senders.activated, cfg["act_mult"], 0.5)
               * np.exp(0.3 * senders.intent.to_numpy()))
        k = rng.poisson(lam)
        idx = np.repeat(np.arange(len(senders)), k)
        if idx.size == 0:
            continue
        sd = senders.iloc[idx]
        n = len(sd)
        ent = (sd.channel == "enterprise").to_numpy()
        rel_ss = rng.choice(["same", "other", "personal"], n, p=cfg["rel"])
        rel_en = rng.choice(["same", "other", "personal"], n, p=ENTERPRISE_REL.get(loop, cfg["rel"]))
        rel = np.where(ent, rel_en, rel_ss)
        sender_acct = sd.account_id_truth.to_numpy()
        rel = np.where((rel == "same") & pd.isna(sender_acct), "personal", rel)
        acct = np.where(rel == "same", sender_acct, None).astype(object)
        o = rel == "other"
        pick = others[rng.integers(0, len(others), o.sum())]
        acct[o] = np.where(pick == sender_acct[o], others[rng.integers(0, len(others), o.sum())], pick)
        rdom = np.array([dom.get(a) if isinstance(a, str) else None for a in acct], dtype=object)
        personal_addr = (rel == "personal") | ((rel == "other") & (rng.random(n) < 0.1))
        rdom[personal_addr] = rng.choice(PERSONAL_DOMAINS, int(personal_addr.sum()))
        licensed = np.array([seg.get(a) == "contract" if isinstance(a, str) else False for a in acct])
        day = sd.signup_week.to_numpy() * 7 + rng.integers(0, 70, n)
        viewed = rng.random(n) < cfg["view"]
        signed = viewed & ~licensed & (rng.random(n) < cfg["signup"])
        sday = day + rng.integers(cfg["delay"][0], cfg["delay"][1], n)
        signed &= (sday // 7) < OBSERVE_WEEKS - 1
        rows.append(pd.DataFrame({
            "sender_id": sd.user_id.to_numpy(), "loop": loop, "share_day": day,
            "sender_licensed": sd.licensed.to_numpy(), "recipient_email_domain": rdom,
            "recipient_licensed": licensed, "viewed": viewed, "signed_up": signed,
            "signup_day": np.where(signed, sday, -1), "recipient_account_truth": acct}))
    ledger = pd.concat(rows, ignore_index=True)
    ledger.insert(0, "share_id", [f"SH{i:06d}" for i in range(len(ledger))])

    rec = ledger[ledger.signed_up].reset_index(drop=True)
    n = len(rec)
    corporate = ~rec.recipient_email_domain.isin(PERSONAL_DOMAINS).to_numpy()
    provider = np.where(corporate, rng.choice(PROVIDERS, n, p=PROVIDER_MIX["corporate"]),
                        rng.choice(PROVIDERS, n, p=PROVIDER_MIX["personal"]))
    edom = rec.recipient_email_domain.to_numpy().copy()
    relay = (provider == "apple") & (rng.random(n) < 0.6)
    edom[relay] = RELAY_DOMAIN
    hide = corporate & (rng.random(n) < pd.Series(provider).map(PERSONAL_ADDRESS_P).to_numpy())
    edom[hide] = rng.choice(PERSONAL_DOMAINS, int(hide.sum()))
    start_id = len(users)
    new = pd.DataFrame({
        "user_id": [f"U{start_id + i:06d}" for i in range(n)],
        "channel": "self_serve", "source": "shared_" + rec.loop, "provider": provider,
        "account_id_truth": rec.recipient_account_truth.to_numpy(), "email_domain": edom,
        "function": rng.choice(FUNCTIONS, n), "signup_week": (rec.signup_day // 7).astype(int).to_numpy(),
        "plan": "free", "rollout_wave": pd.array([pd.NA] * n, dtype="Int64"),
    })
    new["signup_date"] = START_DATE + pd.to_timedelta(new.signup_week * 7, unit="D")
    ledger["recipient_user_id"] = None
    ledger.loc[ledger.signed_up, "recipient_user_id"] = new.user_id.to_numpy()
    return ledger, new


def _conversions(rng, users, truth, accounts) -> pd.DataFrame:
    """Observed outcome: did each prospect company sign an enterprise contract by
    the end of the window? Driven by activated independent users, not sign-ups."""
    prospects = accounts[accounts.segment.str.startswith("prospect")].account_id
    ss = users[(users.channel == "self_serve") & users.account_id_truth.isin(prospects)]
    ss = ss.merge(truth[["user_id", "agent_action_w0"]], on="user_id")
    act = ss[ss.agent_action_w0]
    g = pd.DataFrame({"activated": act.groupby("account_id_truth").size(),
                      "functions": act.groupby("account_id_truth").function.nunique()})
    g = g.reindex(prospects).fillna(0)
    logit = (-4.0 + 2.2 * (g.activated >= THRESHOLD_ACTIVATED)
             + 1.0 * (g.functions >= THRESHOLD_FUNCTIONS) + 0.15 * np.minimum(g.activated, 15))
    p = 1 / (1 + np.exp(-logit))
    return pd.DataFrame({"account_id": prospects.to_numpy(),
                         "converted_to_contract": rng.random(len(p)) < p.to_numpy()})


_TOWNS = ["Maple Grove", "Cedar Falls", "Riverside", "Oak Hollow", "Pine Ridge", "Lakeview",
          "Fairmont", "Brookside", "Highland", "Westbrook", "Sunnydale", "Kingsport"]
_CLUBS = ["FTC Robotics", "Elementary PTA", "Youth Soccer", "Science Olympiad", "Chess Club",
          "Neighborhood Watch", "Running Club"]
_COMMUNITIES = ["k8s-community", "mlops-community", "data-talks", "open-source-ai", "devrel-collective"]


def _slug(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _connections(rng, users, accounts) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Workspaces that self-serve users connect (Slack, Teams, Jira), with traps.

    Real signal: an employee connects their employer's Slack or Teams (which may
    carry a verified company email domain) or Jira site.
    Traps: side-project and school workspaces (an engineer's FTC robotics Slack);
    big open communities; community names that collide with a company name
    ("Ulnex Robotics Boosters" is not Ulnex Holdings); and contractors who are
    guests in a client's workspace."""
    acc = accounts[accounts.segment != "internal"].set_index("account_id")
    ws_rows, link_rows = [], []

    def add_ws(wid, app, name, slug, verified, members, kind, owner=None):
        ws_rows.append({"workspace_id": wid, "app": app, "workspace_name": name, "workspace_slug": slug,
                        "verified_domain": verified, "reported_members": members,
                        "kind_truth": kind, "owner_account_truth": owner})

    # Employer workspaces: each company uses Slack or Teams, and maybe Jira.
    for aid, a in acc.iterrows():
        full = _slug(a.company)
        if rng.random() < 0.7:
            verified = a.domain if rng.random() < 0.7 else None
            add_ws(f"S-{aid}", "slack", a.company, full, verified, int(rng.integers(50, 5000)), "employer", aid)
        else:
            add_ws(f"T-{aid}", "teams", a.company, full, a.domain, int(rng.integers(50, 5000)), "employer", aid)
        if rng.random() < 0.5:
            jira_slug = a.company.lower().replace(" ", "-")
            add_ws(f"J-{aid}", "jira", a.company, jira_slug, None, int(rng.integers(20, 2000)), "employer", aid)
    ws = pd.DataFrame(ws_rows)
    collab = ws[ws.app.isin(["slack", "teams"])].set_index("owner_account_truth").workspace_id
    jira = ws[ws.app == "jira"].set_index("owner_account_truth").workspace_id

    ss = users[users.channel == "self_serve"]
    employed = ss[ss.account_id_truth.notna() & ss.account_id_truth.isin(acc.index)]
    pick = employed[rng.random(len(employed)) < 0.40]
    for uid, aid in zip(pick.user_id, pick.account_id_truth):
        link_rows.append((uid, collab[aid], False))
    pick = employed[(rng.random(len(employed)) < 0.20) & employed.account_id_truth.isin(jira.index)]
    for uid, aid in zip(pick.user_id, pick.account_id_truth):
        link_rows.append((uid, jira[aid], False))
    # Contractors: guests in a client's workspace.
    guests = employed[rng.random(len(employed)) < 0.03]
    others = collab.index.to_numpy()
    for uid, aid in zip(guests.user_id, guests.account_id_truth):
        client = rng.choice(others[others != aid])
        link_rows.append((uid, collab[client], True))

    # Side-project and school workspaces: members from anywhere.
    extra = []
    n = 0
    for town in _TOWNS:
        for club in rng.choice(_CLUBS, 3, replace=False):
            n += 1
            name = f"{town} {club}"
            extra.append((f"C-{n:03d}", name, _slug(name), int(rng.integers(20, 120)), "side_project",
                          int(rng.integers(12, 45))))
    # Name collisions: community workspaces that share a prospect company's stem.
    prospects = accounts[accounts.segment.str.startswith("prospect")]
    for _, a in prospects.sample(15, random_state=rng).iterrows():
        n += 1
        stem = a.company.split()[0]
        name = f"{stem} {rng.choice(['Robotics Boosters', 'Hiking Club', 'Makers', 'Book Club'])}"
        extra.append((f"C-{n:03d}", name, _slug(name), int(rng.integers(20, 150)), "collision",
                      int(rng.integers(12, 35))))
    for name in _COMMUNITIES:
        n += 1
        extra.append((f"C-{n:03d}", name, _slug(name), int(rng.integers(20_000, 90_000)), "community",
                      int(rng.integers(60, 160))))
    for wid, name, slug, members, kind, k in extra:
        add_ws(wid, "slack", name, slug, None, members, kind)
        for uid in ss.user_id.sample(k, random_state=rng):
            link_rows.append((uid, wid, False))

    links = pd.DataFrame(link_rows, columns=["user_id", "workspace_id", "is_guest"]).drop_duplicates(
        ["user_id", "workspace_id"])
    return pd.DataFrame(ws_rows), links


def generate(out_dir: str | Path = "data", cfg: Config | None = None) -> dict[str, Path]:
    cfg = cfg or Config()
    rng = np.random.default_rng(cfg.seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    accounts = _accounts(rng, cfg)
    users = _users(rng, cfg, accounts)
    events, truth = _behavior(rng, users, accounts)
    ledger, loop_users = _loops(rng, users, truth, accounts)
    ev2, tr2 = _behavior(rng, loop_users, accounts)
    users = pd.concat([users, loop_users], ignore_index=True)
    events = pd.concat([events, ev2], ignore_index=True)
    truth = pd.concat([truth, tr2], ignore_index=True)

    outcomes = _conversions(rng, users, truth, accounts)
    workspaces, links = _connections(rng, users, accounts)

    # The analyst never sees the true account; it must be resolved from email.
    public_users = users.drop(columns=["account_id_truth"])
    truth = truth.merge(users[["user_id", "account_id_truth"]], on="user_id")

    paths = {
        "accounts": out / "accounts.csv",
        "users": out / "users.csv",
        "events": out / "events.csv.gz",
        "account_outcomes": out / "account_outcomes.csv",
        "workspaces": out / "workspaces.csv",
        "shares": out / "shares.csv.gz",
        "connections": out / "connections.csv",
        "ground_truth_users": out / "ground_truth" / "users_truth.csv",
        "ground_truth_accounts": out / "ground_truth" / "accounts_truth.csv",
    }
    (out / "ground_truth").mkdir(exist_ok=True)
    accounts.drop(columns=["segment"]).to_csv(paths["accounts"], index=False)
    public_users.to_csv(paths["users"], index=False)
    events.to_csv(paths["events"], index=False)
    outcomes.to_csv(paths["account_outcomes"], index=False)
    workspaces.drop(columns=["kind_truth", "owner_account_truth"]).to_csv(paths["workspaces"], index=False)
    workspaces[["workspace_id", "kind_truth", "owner_account_truth"]].to_csv(
        out / "ground_truth" / "workspaces_truth.csv", index=False)
    links.to_csv(paths["connections"], index=False)
    ledger.drop(columns=["recipient_account_truth"]).to_csv(paths["shares"], index=False)
    ledger[["share_id", "recipient_account_truth"]].to_csv(
        out / "ground_truth" / "shares_truth.csv.gz", index=False)
    truth.to_csv(paths["ground_truth_users"], index=False)
    accounts[["account_id", "segment"]].to_csv(paths["ground_truth_accounts"], index=False)
    (out / "README.md").write_text(
        "# Synthetic data\n\nEvery row in this folder is synthetic, produced by "
        "`sangam/generate.py` with a fixed seed. Company names and `.example` "
        "domains are invented. `ground_truth/` holds the expected results used "
        "only for grading; the analysis never reads it.\n", encoding="utf-8")
    (out / "config.json").write_text(json.dumps(cfg.__dict__, indent=2), encoding="utf-8")
    return paths


if __name__ == "__main__":
    for k, v in generate().items():
        print(f"{k}: {v}")
