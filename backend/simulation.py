"""Twin's deterministic financial simulation engine.

**The LLM never does arithmetic.** Every number the user sees - remaining savings, cash
flow, emergency-fund cover, goal delay, health score, the 12-month projection - is
computed here, in pure Python, from the Financial Twin profile. The LLM receives these
figures as structured data and is only allowed to explain them.

The engine also *writes* deterministic prose: scenario names, one-line verdicts, alert
messages, timeline events. All of that is localised through `i18n.py`, so an Arabic user
gets Arabic strings from the engine itself rather than a translated afterthought.

Numbers are identical in every language. Only their wrapper changes.

The module has no I/O, which makes it fully unit-testable (see tests/test_simulation.py).
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import i18n
from config import (
    CHEAPER_ALTERNATIVE_RATIO,
    CONVENTIONAL_EFFECTIVE_APR,
    DTI_EXCELLENT,
    DTI_FAILING,
    EF_RATIO_MEDIUM,
    EMERGENCY_FUND_MONTHS,
    HEALTH_WEIGHT_DEBT_TO_INCOME,
    HEALTH_WEIGHT_EMERGENCY_FUND,
    HEALTH_WEIGHT_GOAL_PROGRESS,
    HEALTH_WEIGHT_SAVINGS_RATE,
    HEALTHY_SAVINGS_RATE,
    MIN_CASH_FLOW_RATIO_HIGH,
    MIN_CASH_FLOW_RATIO_MEDIUM,
    MURABAHA_FLAT_PROFIT_RATE,
    MURABAHA_TERM_MONTHS,
    TIMELINE_MONTHS,
    WAIT_MONTHS,
    ZAKAT_RATE,
)
from i18n import sar as _sar
from i18n import t
from twin_profile import Goal, Profile

Risk = Literal["low", "medium", "high"]
RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}

# Fidelity = how faithfully a scenario delivers what the user actually asked for.
# It is the first tie-breaker after risk, so that when several options are equally safe
# we recommend the one that gives the user what they wanted rather than the one that
# quietly downgrades their life. Lower is more faithful.
FIDELITY_EXACT = 0  # the item, now, in full
FIDELITY_FINANCED = 1  # the item now, but you pay a markup and mortgage future months
FIDELITY_DELAYED = 2  # the item in full, but later
FIDELITY_COMPROMISED = 3  # a cheaper substitute, or not at all


# -- Small helpers ---------------------------------------------------------------------


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


# -- Data model ------------------------------------------------------------------------


@dataclass
class MonthProjection:
    """One row of a 12-month projection. The ledger reconciles exactly:

    savings[n] = savings[n-1] + income - expenses - purchase
    """

    month: str
    income: float
    expenses: float  # recurring outflow: living costs + debt service + any installment
    purchase: float  # one-off outflow in this month (0 in most months)
    savings: float
    warnings: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    """One way of handling the requested decision, fully costed.

    `key` is a stable identifier ("buy_now", "finance", ...) and is what all internal
    logic keys off. `name` is a display string and may be in any language   never branch
    on it.
    """

    key: str
    name: str
    remaining_savings: float
    monthly_cash_flow: float
    emergency_fund_months: float
    emergency_fund_ok: bool
    risk: Risk
    goal_delay_months: int
    recommendation: str

    # Extra fields the UI uses; harmless to any client that ignores them.
    detail: str = ""
    upfront_cost: float = 0.0
    total_cost: float = 0.0
    monthly_payment: float = 0.0  # new recurring commitment this scenario creates
    health_score: float = 0.0
    health_delta: float = 0.0
    recommended: bool = False
    fidelity: int = FIDELITY_EXACT
    timeline: list[MonthProjection] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationResult:
    scenarios: list[Scenario]
    timeline: list[MonthProjection]  # the recommended scenario's projection
    alert: dict[str, str] | None
    subject: str  # human-readable description of what was simulated
    facts: dict[str, Any]  # extra computed figures for the LLM to cite

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarios": [s.to_dict() for s in self.scenarios],
            "timeline": [asdict(m) for m in self.timeline],
            "alert": self.alert,
            "subject": self.subject,
            "facts": self.facts,
        }


# -- Core financial primitives ---------------------------------------------------------


def health_score(
    *,
    salary: float,
    monthly_expenses: float,
    monthly_debt: float,
    savings: float,
    goal_amount: float,
    emergency_target: float,
    goal_achieved: bool = False,
) -> float:
    """Financial Health Score, 0-100.

    Four weighted components (weights live in config.py and sum to 100):

      1. Savings rate (40 pts)
             rate = (salary - expenses - debt) / salary
         Scaled against HEALTHY_SAVINGS_RATE (20%); a 20%+ rate earns full marks.

      2. Emergency fund coverage (30 pts)
             coverage = savings / (6 x monthly expenses)
         Capped at 1.0 - holding twelve months of expenses is not twice as healthy as
         holding six, it is just idle cash.

      3. Debt-to-income (20 pts), lower is better
             dti = monthly debt payments / salary
         Full marks at or below DTI_EXCELLENT (5%), zero at or above DTI_FAILING (40%),
         linear in between.

      4. Goal progress (10 pts)
             progress = (savings - emergency target) / primary goal amount
         Only savings *above* the emergency-fund floor count toward a goal: money you
         would have to raid your buffer to spend is not progress. If the decision being
         simulated actually achieves the goal (you bought the car), it scores full marks.
    """
    # 1. Savings rate.
    surplus = salary - monthly_expenses - monthly_debt
    savings_rate = surplus / salary if salary > 0 else 0.0
    pts_savings_rate = _clamp(savings_rate / HEALTHY_SAVINGS_RATE) * HEALTH_WEIGHT_SAVINGS_RATE

    # 2. Emergency fund coverage.
    coverage = savings / emergency_target if emergency_target > 0 else 1.0
    pts_emergency = _clamp(coverage) * HEALTH_WEIGHT_EMERGENCY_FUND

    # 3. Debt-to-income.
    dti = monthly_debt / salary if salary > 0 else 0.0
    dti_quality = (DTI_FAILING - dti) / (DTI_FAILING - DTI_EXCELLENT)
    pts_debt = _clamp(dti_quality) * HEALTH_WEIGHT_DEBT_TO_INCOME

    # 4. Goal progress.
    if goal_achieved or goal_amount <= 0:
        progress = 1.0
    else:
        investable = max(0.0, savings - emergency_target)
        progress = investable / goal_amount
    pts_goal = _clamp(progress) * HEALTH_WEIGHT_GOAL_PROGRESS

    total = pts_savings_rate + pts_emergency + pts_debt + pts_goal
    return round(total, 1)


def score_label(score: float, lang: str = "en") -> str:
    if score >= 85:
        return t("health.excellent", lang)
    if score >= 70:
        return t("health.good", lang)
    if score >= 50:
        return t("health.fair", lang)
    if score >= 30:
        return t("health.at_risk", lang)
    return t("health.critical", lang)


def health_breakdown(profile: Profile, lang: str = "en") -> dict[str, Any]:
    """The baseline score plus its four components, for the dashboard gauge."""
    goal = profile.primary_goal
    goal_amount = goal.amount if goal else 0.0
    target = profile.emergency_fund_target

    surplus = profile.monthly_surplus
    savings_rate = surplus / profile.salary if profile.salary else 0.0
    dti = profile.monthly_debt / profile.salary if profile.salary else 0.0
    coverage = profile.savings / target if target else 1.0
    investable = max(0.0, profile.savings - target)
    progress = _clamp(investable / goal_amount) if goal_amount else 1.0

    score = health_score(
        salary=profile.salary,
        monthly_expenses=profile.monthly_expenses,
        monthly_debt=profile.monthly_debt,
        savings=profile.savings,
        goal_amount=goal_amount,
        emergency_target=target,
    )
    return {
        "score": score,
        "label": score_label(score, lang),
        "components": [
            {
                "name": t("health.savings_rate", lang),
                "value": round(savings_rate * 100, 1),
                "unit": "%",
                "points": round(_clamp(savings_rate / HEALTHY_SAVINGS_RATE) * 40, 1),
                "max_points": HEALTH_WEIGHT_SAVINGS_RATE,
            },
            {
                "name": t("health.emergency_fund", lang),
                "value": round(min(coverage, 99) * EMERGENCY_FUND_MONTHS, 1),
                "unit": t("unit.months", lang),
                "points": round(_clamp(coverage) * 30, 1),
                "max_points": HEALTH_WEIGHT_EMERGENCY_FUND,
            },
            {
                "name": t("health.debt_to_income", lang),
                "value": round(dti * 100, 1),
                "unit": "%",
                "points": round(
                    _clamp((DTI_FAILING - dti) / (DTI_FAILING - DTI_EXCELLENT)) * 20, 1
                ),
                "max_points": HEALTH_WEIGHT_DEBT_TO_INCOME,
            },
            {
                "name": t("health.goal_progress", lang),
                "value": round(progress * 100, 1),
                "unit": "%",
                "points": round(progress * 10, 1),
                "max_points": HEALTH_WEIGHT_GOAL_PROGRESS,
            },
        ],
    }


def emergency_fund_months(savings: float, monthly_expenses: float) -> float:
    """How many months of expenses the liquid savings would cover."""
    if monthly_expenses <= 0:
        return 0.0
    return round(savings / monthly_expenses, 1)


def risk_level(
    *, savings_after: float, cash_flow: float, salary: float, emergency_target: float
) -> Risk:
    """Rule-based risk rating.

    HIGH   - the emergency fund is broken, or monthly cash flow drops below 10% of
             salary (which includes any negative cash flow).
    MEDIUM - savings fall below 1.5x the emergency target, or cash flow drops below
             25% of salary. Survivable, but the margin is thin.
    LOW    - neither.
    """
    if savings_after < emergency_target or cash_flow < salary * MIN_CASH_FLOW_RATIO_HIGH:
        return "high"
    if (
        savings_after < emergency_target * EF_RATIO_MEDIUM
        or cash_flow < salary * MIN_CASH_FLOW_RATIO_MEDIUM
    ):
        return "medium"
    return "low"


def months_to_afford(
    *, savings: float, target_amount: float, emergency_target: float, surplus: float
) -> int:
    """Months of saving needed before `target_amount` can be paid without touching the
    emergency fund. Returns 0 if it is already affordable."""
    needed = target_amount + emergency_target
    if savings >= needed:
        return 0
    if surplus <= 0:
        return 999  # unreachable at the current burn rate
    return math.ceil((needed - savings) / surplus)


def murabaha(
    amount: float,
    *,
    rate: float = MURABAHA_FLAT_PROFIT_RATE,
    term: int = MURABAHA_TERM_MONTHS,
) -> dict[str, float]:
    """Murabaha (Islamic cost-plus sale): the bank buys the asset and resells it to you
    at a disclosed markup, fixed on day one. Flat markup applied once over the term.

        profit  = amount x rate
        total   = amount + profit
        monthly = total / term
    """
    profit = amount * rate
    total = amount + profit
    return {
        "profit": round(profit, 2),
        "total": round(total, 2),
        "monthly": round(total / term, 2),
        "term": term,
    }


def conventional_loan(
    amount: float,
    *,
    apr: float = CONVENTIONAL_EFFECTIVE_APR,
    term: int = MURABAHA_TERM_MONTHS,
) -> dict[str, float]:
    """A conventional (riba-based) loan for comparison: compounding interest on a
    declining balance, standard amortisation.

        r   = apr / 12
        pmt = P x r / (1 - (1 + r)^-n)
    """
    r = apr / 12
    if r == 0:
        monthly = amount / term
    else:
        monthly = amount * r / (1 - (1 + r) ** -term)
    total = monthly * term
    return {
        "profit": round(total - amount, 2),
        "total": round(total, 2),
        "monthly": round(monthly, 2),
        "term": term,
        "apr": apr,
    }


def zakat_due(zakatable_wealth: float) -> float:
    """2.5% on eligible wealth. Personal-use assets (a car, a home) are exempt, so
    converting cash into one lowers the zakat base."""
    return round(max(0.0, zakatable_wealth) * ZAKAT_RATE, 2)


# -- Projection ------------------------------------------------------------------------


def project(
    profile: Profile,
    *,
    months: int = TIMELINE_MONTHS,
    savings_start: float | None = None,
    salary: float | None = None,
    monthly_expenses: float | None = None,
    extra_monthly_payment: float = 0.0,
    extra_payment_months: int = 0,
    purchase_month: int | None = None,
    purchase_amount: float = 0.0,
    purchase_event: str = "",
    clear_loans: bool = False,
    opening_events: list[str] | None = None,
    lang: str = "en",
) -> list[MonthProjection]:
    """Month-by-month cash projection.

    Handles the existing liabilities correctly: each loan stops consuming cash once its
    `months_remaining` runs out, and that payoff is emitted as an event (a raise you gave
    yourself). Any new financing (`extra_monthly_payment`) runs for
    `extra_payment_months`.
    """
    savings = profile.savings if savings_start is None else savings_start
    salary = profile.salary if salary is None else salary
    expenses = profile.monthly_expenses if monthly_expenses is None else monthly_expenses
    emergency_target = expenses * EMERGENCY_FUND_MONTHS

    rows: list[MonthProjection] = []
    already_warned = False

    for m in range(1, months + 1):
        events: list[str] = []
        warnings: list[str] = []

        if m == 1 and opening_events:
            events.extend(opening_events)

        # Existing debt service, unless this scenario paid the loans off up front.
        debt = 0.0
        if not clear_loans:
            for loan in profile.liabilities:
                if m <= loan.months_remaining:
                    debt += loan.monthly_payment
                    if m == loan.months_remaining:
                        events.append(
                            t(
                                "event.loan_cleared",
                                lang,
                                name=profile.label(loan.name, lang),
                                amount=_sar(loan.monthly_payment, lang),
                            )
                        )

        # New financing introduced by this scenario.
        installment = extra_monthly_payment if m <= extra_payment_months else 0.0
        if extra_monthly_payment > 0 and m == extra_payment_months:
            events.append(
                t("event.financing_done", lang, amount=_sar(extra_monthly_payment, lang))
            )

        purchase = 0.0
        if purchase_month is not None and m == purchase_month and purchase_amount > 0:
            purchase = purchase_amount
            if purchase_event:
                events.append(purchase_event)

        outflow = expenses + debt + installment
        savings = savings + salary - outflow - purchase

        if savings < emergency_target:
            if not already_warned:
                warnings.append(
                    t("warn.below_ef", lang, target=_sar(emergency_target, lang))
                )
                already_warned = True
            else:
                warnings.append(t("warn.still_below", lang))
        if savings < 0:
            warnings.append(t("warn.exhausted", lang))

        rows.append(
            MonthProjection(
                month=i18n.month_label(m, lang),
                income=round(salary, 2),
                expenses=round(outflow, 2),
                purchase=round(purchase, 2),
                savings=round(savings, 2),
                warnings=warnings,
                events=events,
            )
        )

    return rows


def baseline_timeline(
    profile: Profile, months: int = TIMELINE_MONTHS, lang: str = "en"
) -> list[MonthProjection]:
    """The do-nothing projection shown on the dashboard."""
    opening = [
        t(
            "event.liability",
            lang,
            name=profile.label(loan.name, lang),
            amount=_sar(loan.monthly_payment, lang),
            months=loan.months_remaining,
        )
        for loan in profile.liabilities
    ]
    return project(profile, months=months, opening_events=opening, lang=lang)


# -- Goal handling ---------------------------------------------------------------------

# Words that carry no identifying information when matching a purchase to a goal.
_GOAL_STOPWORDS = {
    "buy", "the", "new", "get", "and", "for", "within", "trip",
    "شراء", "رحلة", "على", "من",
}


def _words(text: str) -> set[str]:
    """Latin words of 3+ chars, plus any Arabic word. Lets an Arabic item ("سيارة") match
    an English goal ("Buy a car") through the goal's Arabic label."""
    latin = {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2}
    arabic = set(re.findall(r"[؀-ۿ]+", text))
    return (latin | arabic) - _GOAL_STOPWORDS


def _goal_matches_item(goal: Goal, item: str, profile: Profile) -> bool:
    """Does this purchase satisfy the goal? 'Buy a car' is satisfied by buying a car  
    in either language."""
    if not item:
        return False
    goal_words = _words(goal.name) | _words(profile.label(goal.name, "ar"))
    return bool(goal_words & _words(item))


def _reference_goal(profile: Profile, item: str) -> Goal | None:
    """The goal we measure delay against.

    If the thing being bought *is* the primary goal, delaying that goal is meaningless
    (you are achieving it), so we measure the knock-on delay to the next goal instead.
    """
    for goal in profile.goals:
        if not _goal_matches_item(goal, item, profile):
            return goal
    return None


# -- Scenario construction -------------------------------------------------------------


def _build_scenario(
    profile: Profile,
    *,
    key: str,
    name: str,
    detail: str,
    savings_after: float,
    salary: float,
    monthly_expenses: float,
    monthly_debt: float,
    upfront_cost: float,
    total_cost: float,
    new_monthly_payment: float,
    deferral_months: int,
    item: str,
    goal_achieved: bool,
    fidelity: int,
    baseline_health: float,
    timeline: list[MonthProjection],
) -> Scenario:
    """Assemble one scenario card from an already-computed end state."""
    cash_flow = salary - monthly_expenses - monthly_debt
    emergency_target = monthly_expenses * EMERGENCY_FUND_MONTHS
    ef_months = emergency_fund_months(savings_after, monthly_expenses)
    ef_ok = savings_after >= emergency_target

    risk = risk_level(
        savings_after=savings_after,
        cash_flow=cash_flow,
        salary=salary,
        emergency_target=emergency_target,
    )

    # Goal delay = how long this choice pushes the purchase back (0 unless you wait)
    # + the knock-on delay it causes to your other goals.
    ref = _reference_goal(profile, item)
    knock_on = 0
    if ref:
        before = months_to_afford(
            savings=profile.savings,
            target_amount=ref.amount,
            emergency_target=profile.emergency_fund_target,
            surplus=profile.monthly_surplus,
        )
        after = months_to_afford(
            savings=savings_after,
            target_amount=ref.amount,
            emergency_target=emergency_target,
            surplus=cash_flow,
        )
        knock_on = max(0, after - before)

    score = health_score(
        salary=salary,
        monthly_expenses=monthly_expenses,
        monthly_debt=monthly_debt,
        savings=savings_after,
        goal_amount=profile.primary_goal.amount if profile.primary_goal else 0.0,
        emergency_target=emergency_target,
        goal_achieved=goal_achieved,
    )

    return Scenario(
        key=key,
        name=name,
        detail=detail,
        remaining_savings=round(savings_after, 2),
        monthly_cash_flow=round(cash_flow, 2),
        emergency_fund_months=ef_months,
        emergency_fund_ok=ef_ok,
        risk=risk,
        goal_delay_months=deferral_months + knock_on,
        recommendation="",  # filled in by _write_recommendation once risk is known
        upfront_cost=round(upfront_cost, 2),
        total_cost=round(total_cost, 2),
        monthly_payment=round(new_monthly_payment, 2),
        health_score=score,
        health_delta=round(score - baseline_health, 1),
        fidelity=fidelity,
        timeline=timeline,
    )


def _write_recommendation(scenario: Scenario, profile: Profile, lang: str) -> str:
    """One-line, rule-based verdict. Deterministic - no LLM involved."""
    if not scenario.emergency_fund_ok:
        return t(
            "rec.breaks_ef",
            lang,
            savings=_sar(scenario.remaining_savings, lang),
            target=_sar(profile.emergency_fund_target, lang),
        )
    if scenario.risk == "high":
        return t(
            "rec.high",
            lang,
            cash=_sar(scenario.monthly_cash_flow, lang),
            salary=_sar(profile.salary, lang),
        )
    if scenario.risk == "medium":
        return t(
            "rec.medium",
            lang,
            cash=_sar(scenario.monthly_cash_flow, lang),
            cover=scenario.emergency_fund_months,
        )
    return t(
        "rec.low",
        lang,
        cover=scenario.emergency_fund_months,
        cash=_sar(scenario.monthly_cash_flow, lang),
    )


def _rank(scenarios: list[Scenario]) -> None:
    """Pick the recommended scenario and flag it.

    Order of preference: lowest risk first; among equally safe options, the one that most
    faithfully gives the user what they asked for; then the healthiest; then the cheapest.
    Safety is never traded for fidelity - a high-risk "you get exactly what you wanted"
    always loses to a low-risk alternative.
    """
    if not scenarios:
        return
    best = min(
        scenarios,
        key=lambda s: (RISK_ORDER[s.risk], s.fidelity, -s.health_score, s.total_cost),
    )
    best.recommended = True


def _build_alert(
    profile: Profile,
    immediate: Scenario,
    scenarios: list[Scenario],
    subject: str,
    lang: str,
) -> dict[str, str] | None:
    """The 'Twin protects you' moment.

    DANGER if acting immediately would break the emergency fund or leave cash flow
    critically thin. WARNING if the margin gets uncomfortably narrow. Otherwise an INFO
    all-clear, so the user always gets an explicit verdict rather than silence.
    """
    target = profile.emergency_fund_target
    subject_cased = i18n.sentence_case(subject, lang)
    first_breach = next((m.month for m in immediate.timeline if m.savings < target), None)

    if immediate.remaining_savings < 0:
        return {
            "level": "danger",
            "message": t(
                "alert.cannot_pay",
                lang,
                subject=subject,
                cost=_sar(immediate.upfront_cost, lang),
                savings=_sar(profile.savings, lang),
            ),
        }

    if not immediate.emergency_fund_ok:
        breach = (
            t("alert.breach_suffix", lang, month=first_breach) if first_breach else ""
        )
        return {
            "level": "danger",
            "message": t(
                "alert.breaks_ef",
                lang,
                subject=subject_cased,
                savings=_sar(immediate.remaining_savings, lang),
                target=_sar(target, lang),
                ef_months=EMERGENCY_FUND_MONTHS,
                breach=breach,
                cover=immediate.emergency_fund_months,
            ),
        }

    if immediate.monthly_cash_flow < profile.salary * MIN_CASH_FLOW_RATIO_HIGH:
        return {
            "level": "danger",
            "message": t(
                "alert.thin_cash",
                lang,
                subject=subject_cased,
                cash=_sar(immediate.monthly_cash_flow, lang),
            ),
        }

    if immediate.risk == "medium":
        return {
            "level": "warning",
            "message": t(
                "alert.medium",
                lang,
                subject=subject_cased,
                savings=_sar(immediate.remaining_savings, lang),
                cash=_sar(immediate.monthly_cash_flow, lang),
                cover=immediate.emergency_fund_months,
            ),
        }

    if any(s.risk == "high" for s in scenarios):
        risky = next(s for s in scenarios if s.risk == "high")
        return {
            "level": "warning",
            "message": t(
                "alert.risky_route",
                lang,
                name=risky.name,
                cash=_sar(risky.monthly_cash_flow, lang),
            ),
        }

    return {
        "level": "info",
        "message": t(
            "alert.ok",
            lang,
            subject=subject_cased,
            target=_sar(target, lang),
            cover=immediate.emergency_fund_months,
            cash=_sar(immediate.monthly_cash_flow, lang),
        ),
    }


def _baseline_health(profile: Profile) -> float:
    return health_score(
        salary=profile.salary,
        monthly_expenses=profile.monthly_expenses,
        monthly_debt=profile.monthly_debt,
        savings=profile.savings,
        goal_amount=profile.primary_goal.amount if profile.primary_goal else 0.0,
        emergency_target=profile.emergency_fund_target,
    )


# -- Public entry points ---------------------------------------------------------------


def simulate_purchase(
    profile: Profile,
    *,
    item: str,
    price: float,
    recurring: bool = False,
    financing_option: str | None = None,
    lang: str = "en",
) -> SimulationResult:
    """Simulate a purchase and return every option, costed."""
    lang = i18n.normalize(lang)
    if recurring:
        return _simulate_recurring(profile, item=item, monthly_price=price, lang=lang)
    return _simulate_one_off(
        profile, item=item, price=price, financing_option=financing_option, lang=lang
    )


def _simulate_one_off(
    profile: Profile, *, item: str, price: float, financing_option: str | None, lang: str
) -> SimulationResult:
    """The four scenarios from the spec: Buy Now, Wait 6 Months, Finance, Cheaper."""
    base_health = _baseline_health(profile)
    surplus = profile.monthly_surplus
    goal_hit = any(_goal_matches_item(g, item, profile) for g in profile.goals)
    label = item or t("item.fallback", lang)

    scenarios: list[Scenario] = []

    # 1. BUY NOW - pay cash from savings.
    buy_now = _build_scenario(
        profile,
        key="buy_now",
        name=t("scenario.buy_now", lang),
        detail=t("detail.buy_now", lang, price=_sar(price, lang)),
        savings_after=profile.savings - price,
        salary=profile.salary,
        monthly_expenses=profile.monthly_expenses,
        monthly_debt=profile.monthly_debt,
        upfront_cost=price,
        total_cost=price,
        new_monthly_payment=0.0,
        deferral_months=0,
        item=item,
        goal_achieved=goal_hit,
        fidelity=FIDELITY_EXACT,
        baseline_health=base_health,
        timeline=project(
            profile,
            purchase_month=1,
            purchase_amount=price,
            purchase_event=t(
                "event.bought", lang, item=label, amount=_sar(price, lang)
            ),
            lang=lang,
        ),
    )
    scenarios.append(buy_now)

    # 2. WAIT 6 MONTHS - keep saving the monthly surplus, then pay cash.
    saved_by_then = profile.savings + surplus * WAIT_MONTHS
    scenarios.append(
        _build_scenario(
            profile,
            key="wait",
            name=t("scenario.wait", lang, months=WAIT_MONTHS),
            detail=t(
                "detail.wait",
                lang,
                surplus=_sar(surplus, lang),
                months=WAIT_MONTHS,
                added=_sar(surplus * WAIT_MONTHS, lang),
            ),
            savings_after=saved_by_then - price,
            salary=profile.salary,
            monthly_expenses=profile.monthly_expenses,
            monthly_debt=profile.monthly_debt,
            upfront_cost=price,
            total_cost=price,
            new_monthly_payment=0.0,
            deferral_months=WAIT_MONTHS,
            item=item,
            goal_achieved=goal_hit,
            fidelity=FIDELITY_DELAYED,
            baseline_health=base_health,
            timeline=project(
                profile,
                purchase_month=WAIT_MONTHS,
                purchase_amount=price,
                purchase_event=t(
                    "event.bought", lang, item=label, amount=_sar(price, lang)
                ),
                lang=lang,
            ),
        )
    )

    # 3. FINANCE - murabaha, with the conventional equivalent shown for comparison.
    plan = murabaha(price)
    conv = conventional_loan(price)
    scenarios.append(
        _build_scenario(
            profile,
            key="finance",
            name=t("scenario.finance", lang),
            detail=t(
                "detail.finance",
                lang,
                monthly=_sar(plan["monthly"], lang),
                term=plan["term"],
                total=_sar(plan["total"], lang),
                profit=_sar(plan["profit"], lang),
                apr=f"{conv['apr'] * 100:.1f}",
                conv_total=_sar(conv["total"], lang),
            ),
            savings_after=profile.savings,  # cash stays in the bank
            salary=profile.salary,
            monthly_expenses=profile.monthly_expenses,
            monthly_debt=profile.monthly_debt + plan["monthly"],
            upfront_cost=0.0,
            total_cost=plan["total"],
            new_monthly_payment=plan["monthly"],
            deferral_months=0,
            item=item,
            goal_achieved=goal_hit,
            fidelity=FIDELITY_FINANCED,
            baseline_health=base_health,
            timeline=project(
                profile,
                extra_monthly_payment=plan["monthly"],
                extra_payment_months=plan["term"],
                opening_events=[
                    t(
                        "event.financed",
                        lang,
                        item=label,
                        amount=_sar(plan["monthly"], lang),
                        term=plan["term"],
                    )
                ],
                lang=lang,
            ),
        )
    )

    # 4. CHEAPER ALTERNATIVE - 65% of the asked price.
    cheaper_price = round(price * CHEAPER_ALTERNATIVE_RATIO, 2)
    scenarios.append(
        _build_scenario(
            profile,
            key="cheaper",
            name=t("scenario.cheaper", lang),
            detail=t(
                "detail.cheaper",
                lang,
                price=_sar(cheaper_price, lang),
                ratio=f"{CHEAPER_ALTERNATIVE_RATIO * 100:.0f}",
                saved=_sar(price - cheaper_price, lang),
            ),
            savings_after=profile.savings - cheaper_price,
            salary=profile.salary,
            monthly_expenses=profile.monthly_expenses,
            monthly_debt=profile.monthly_debt,
            upfront_cost=cheaper_price,
            total_cost=cheaper_price,
            new_monthly_payment=0.0,
            deferral_months=0,
            item=item,
            goal_achieved=goal_hit,
            fidelity=FIDELITY_COMPROMISED,
            baseline_health=base_health,
            timeline=project(
                profile,
                purchase_month=1,
                purchase_amount=cheaper_price,
                purchase_event=t(
                    "event.bought_cheaper",
                    lang,
                    item=label,
                    amount=_sar(cheaper_price, lang),
                ),
                lang=lang,
            ),
        )
    )

    for s in scenarios:
        s.recommendation = _write_recommendation(s, profile, lang)

    # If the user asked about a specific route ("what if I wait six months?"), lead with
    # that card. Note this only changes the *order*: _rank still recommends the safest
    # option, so asking about a risky route never talks the Twin into endorsing it.
    # Matching is on the stable `key`, never on the translated name.
    if financing_option:
        asked = financing_option.lower()
        preferred = None
        if any(w in asked for w in ("financ", "murabaha", "instal", "loan", "تمويل", "مرابحة")):
            preferred = "finance"
        elif any(w in asked for w in ("wait", "delay", "postpone", "later", "انتظر", "تأجيل")):
            preferred = "wait"
        elif any(w in asked for w in ("cash", "now", "outright", "نقد", "الآن")):
            preferred = "buy_now"
        elif any(w in asked for w in ("cheap", "alternative", "أرخص", "بديل")):
            preferred = "cheaper"
        if preferred:
            scenarios.sort(key=lambda s: 0 if s.key == preferred else 1)

    _rank(scenarios)

    subject = t(
        "subject.purchase",
        lang,
        item=i18n.with_article(label, lang),
        price=_sar(price, lang),
    )
    recommended = next(s for s in scenarios if s.recommended)
    alert = _build_alert(profile, buy_now, scenarios, subject, lang)

    facts = {
        "price": price,
        "item": label,
        "savings_before": profile.savings,
        "monthly_surplus_before": surplus,
        "emergency_fund_target": profile.emergency_fund_target,
        "murabaha": plan,
        "conventional": conv,
        "zakat_before": zakat_due(profile.zakatable_wealth),
        # A personal-use asset is exempt from zakat, so paying cash shrinks the base.
        "zakat_after_cash_purchase": zakat_due(profile.zakatable_wealth - price),
        "price_as_pct_of_savings": round(price / profile.savings * 100, 1)
        if profile.savings
        else None,
        "baseline_health_score": base_health,
        "recommended_scenario": recommended.name,
    }

    return SimulationResult(
        scenarios=scenarios,
        timeline=recommended.timeline,
        alert=alert,
        subject=subject,
        facts=facts,
    )


def _simulate_recurring(
    profile: Profile, *, item: str, monthly_price: float, lang: str
) -> SimulationResult:
    """A recurring commitment (a subscription) is not a one-off purchase: it does not
    dent your savings, it permanently narrows your monthly cash flow. Different question,
    different scenarios."""
    base_health = _baseline_health(profile)
    # The extractor may not name the item ("can I afford 300 a month?"). "Subscription" is
    # a better fallback noun here than the generic one, because it reads correctly in the
    # subject line: "a 300 SAR/month subscription".
    generic = t("item.fallback", lang)
    label = item if item and item != generic else t("item.subscription", lang)
    annual = monthly_price * 12
    surplus = profile.monthly_surplus

    scenarios: list[Scenario] = []

    # 1. SUBSCRIBE NOW - the commitment lands on cash flow, every month, forever.
    subscribe = _build_scenario(
        profile,
        key="subscribe_now",
        name=t("scenario.subscribe_now", lang),
        detail=t(
            "detail.subscribe_now",
            lang,
            monthly=_sar(monthly_price, lang),
            annual=_sar(annual, lang),
            pct=f"{monthly_price / surplus * 100:.1f}" if surplus else " ",
        ),
        savings_after=profile.savings,
        salary=profile.salary,
        monthly_expenses=profile.monthly_expenses + monthly_price,
        monthly_debt=profile.monthly_debt,
        upfront_cost=0.0,
        total_cost=annual,
        new_monthly_payment=monthly_price,
        deferral_months=0,
        item=item,
        goal_achieved=False,
        fidelity=FIDELITY_EXACT,
        baseline_health=base_health,
        timeline=project(
            profile,
            monthly_expenses=profile.monthly_expenses + monthly_price,
            opening_events=[
                t(
                    "event.subscribed",
                    lang,
                    item=label,
                    amount=_sar(monthly_price, lang),
                )
            ],
            lang=lang,
        ),
    )
    scenarios.append(subscribe)

    # 2. ANNUAL PREPAY - most providers give ~2 months free for paying up front.
    prepay = round(monthly_price * 10, 2)
    scenarios.append(
        _build_scenario(
            profile,
            key="pay_annually",
            name=t("scenario.pay_annually", lang),
            detail=t(
                "detail.pay_annually",
                lang,
                prepay=_sar(prepay, lang),
                annual=_sar(annual, lang),
                saved=_sar(annual - prepay, lang),
            ),
            savings_after=profile.savings - prepay,
            salary=profile.salary,
            monthly_expenses=profile.monthly_expenses,
            monthly_debt=profile.monthly_debt,
            upfront_cost=prepay,
            total_cost=prepay,
            new_monthly_payment=0.0,
            deferral_months=0,
            item=item,
            goal_achieved=False,
            fidelity=FIDELITY_FINANCED,
            baseline_health=base_health,
            timeline=project(
                profile,
                purchase_month=1,
                purchase_amount=prepay,
                purchase_event=t(
                    "event.annual_plan", lang, item=label, amount=_sar(prepay, lang)
                ),
                lang=lang,
            ),
        )
    )

    # 3. CHEAPER TIER.
    cheaper = round(monthly_price * CHEAPER_ALTERNATIVE_RATIO, 2)
    scenarios.append(
        _build_scenario(
            profile,
            key="cheaper_tier",
            name=t("scenario.cheaper_tier", lang),
            detail=t(
                "detail.cheaper_tier",
                lang,
                monthly=_sar(cheaper, lang),
                saved=_sar((monthly_price - cheaper) * 12, lang),
            ),
            savings_after=profile.savings,
            salary=profile.salary,
            monthly_expenses=profile.monthly_expenses + cheaper,
            monthly_debt=profile.monthly_debt,
            upfront_cost=0.0,
            total_cost=cheaper * 12,
            new_monthly_payment=cheaper,
            deferral_months=0,
            item=item,
            goal_achieved=False,
            fidelity=FIDELITY_COMPROMISED,
            baseline_health=base_health,
            timeline=project(
                profile,
                monthly_expenses=profile.monthly_expenses + cheaper,
                lang=lang,
            ),
        )
    )

    # 4. SKIP IT - the counterfactual, so the cost of saying yes is visible.
    scenarios.append(
        _build_scenario(
            profile,
            key="skip",
            name=t("scenario.skip", lang),
            detail=t(
                "detail.skip",
                lang,
                monthly=_sar(monthly_price, lang),
                annual=_sar(annual, lang),
            ),
            savings_after=profile.savings,
            salary=profile.salary,
            monthly_expenses=profile.monthly_expenses,
            monthly_debt=profile.monthly_debt,
            upfront_cost=0.0,
            total_cost=0.0,
            new_monthly_payment=0.0,
            deferral_months=0,
            item=item,
            goal_achieved=False,
            fidelity=FIDELITY_COMPROMISED + 1,
            baseline_health=base_health,
            timeline=project(profile, lang=lang),
        )
    )

    for s in scenarios:
        s.recommendation = _write_recommendation(s, profile, lang)
    _rank(scenarios)

    subject = t(
        "subject.recurring", lang, price=_sar(monthly_price, lang), item=label
    )
    recommended = next(s for s in scenarios if s.recommended)
    alert = _build_alert(profile, subscribe, scenarios, subject, lang)

    facts = {
        "monthly_price": monthly_price,
        "annual_cost": annual,
        "item": label,
        "monthly_surplus_before": surplus,
        "pct_of_surplus": round(monthly_price / surplus * 100, 1) if surplus else None,
        "pct_of_salary": round(monthly_price / profile.salary * 100, 1),
        "emergency_fund_target": profile.emergency_fund_target,
        "baseline_health_score": base_health,
        "recommended_scenario": recommended.name,
        "recurring": True,
    }

    return SimulationResult(
        scenarios=scenarios,
        timeline=recommended.timeline,
        alert=alert,
        subject=subject,
        facts=facts,
    )


def simulate_income_shock(
    profile: Profile, *, change_pct: float, lang: str = "en"
) -> SimulationResult:
    """What happens if salary changes by `change_pct` (e.g. -20 for a 20% pay cut).

    Same card schema as a purchase, so the UI renders it with no special-casing.

    Note that every scenario here carries the same fidelity: unlike a purchase, there is
    no "thing the user asked for" to be faithful to, so the ranking falls straight through
    to the health score. That is the right answer - if clearing the loan leaves you
    healthier than doing nothing, the Twin should say so rather than defaulting to inertia.
    """
    lang = i18n.normalize(lang)
    base_health = _baseline_health(profile)
    new_salary = round(profile.salary * (1 + change_pct / 100), 2)
    delta = profile.salary - new_salary
    direction = t("direction.drop" if change_pct < 0 else "direction.rise", lang)
    subject = t(
        "subject.income", lang, pct=f"{abs(change_pct):.0f}", direction=direction
    )

    scenarios: list[Scenario] = []

    # 1. ABSORB IT - change nothing and take the hit on cash flow.
    absorb = _build_scenario(
        profile,
        key="absorb",
        name=t("scenario.absorb", lang),
        detail=t(
            "detail.absorb",
            lang,
            salary=_sar(new_salary, lang),
            delta=_sar(abs(delta), lang),
        ),
        savings_after=profile.savings,
        salary=new_salary,
        monthly_expenses=profile.monthly_expenses,
        monthly_debt=profile.monthly_debt,
        upfront_cost=0.0,
        total_cost=abs(delta) * 12,
        new_monthly_payment=0.0,
        deferral_months=0,
        item="",
        goal_achieved=False,
        fidelity=FIDELITY_EXACT,
        baseline_health=base_health,
        timeline=project(
            profile,
            salary=new_salary,
            opening_events=[
                t("event.salary_change", lang, amount=_sar(new_salary, lang))
            ],
            lang=lang,
        ),
    )
    scenarios.append(absorb)

    # 2. TRIM SPENDING - cut discretionary spending 15% to protect the surplus.
    trimmed_expenses = round(profile.monthly_expenses * 0.85, 2)
    saved = profile.monthly_expenses - trimmed_expenses
    scenarios.append(
        _build_scenario(
            profile,
            key="trim",
            name=t("scenario.trim", lang),
            detail=t(
                "detail.trim",
                lang,
                expenses=_sar(trimmed_expenses, lang),
                saved=_sar(saved, lang),
                target=_sar(trimmed_expenses * EMERGENCY_FUND_MONTHS, lang),
            ),
            savings_after=profile.savings,
            salary=new_salary,
            monthly_expenses=trimmed_expenses,
            monthly_debt=profile.monthly_debt,
            upfront_cost=0.0,
            total_cost=0.0,
            new_monthly_payment=0.0,
            deferral_months=0,
            item="",
            goal_achieved=False,
            fidelity=FIDELITY_EXACT,
            baseline_health=base_health,
            timeline=project(
                profile,
                salary=new_salary,
                monthly_expenses=trimmed_expenses,
                lang=lang,
            ),
        )
    )

    # 3. CLEAR THE LOAN - settle the outstanding debt from savings to restore cash flow.
    payoff = sum(
        loan.monthly_payment * loan.months_remaining for loan in profile.liabilities
    )
    if payoff > 0:
        scenarios.append(
            _build_scenario(
                profile,
                key="clear_loan",
                name=t("scenario.clear_loan", lang),
                detail=t(
                    "detail.clear_loan",
                    lang,
                    payoff=_sar(payoff, lang),
                    monthly=_sar(profile.monthly_debt, lang),
                ),
                savings_after=profile.savings - payoff,
                salary=new_salary,
                monthly_expenses=profile.monthly_expenses,
                monthly_debt=0.0,
                upfront_cost=payoff,
                total_cost=payoff,
                new_monthly_payment=0.0,
                deferral_months=0,
                item="",
                goal_achieved=False,
                fidelity=FIDELITY_EXACT,
                baseline_health=base_health,
                timeline=project(
                    profile,
                    salary=new_salary,
                    savings_start=profile.savings - payoff,
                    clear_loans=True,
                    opening_events=[
                        t(
                            "event.loan_settled",
                            lang,
                            amount=_sar(payoff, lang),
                            monthly=_sar(profile.monthly_debt, lang),
                        )
                    ],
                    lang=lang,
                ),
            )
        )

    for s in scenarios:
        s.recommendation = _write_recommendation(s, profile, lang)
    _rank(scenarios)

    recommended = next(s for s in scenarios if s.recommended)
    alert = _build_alert(profile, absorb, scenarios, subject, lang)

    facts = {
        "old_salary": profile.salary,
        "new_salary": new_salary,
        "change_pct": change_pct,
        "monthly_surplus_before": profile.monthly_surplus,
        "monthly_surplus_after": absorb.monthly_cash_flow,
        "emergency_fund_target": profile.emergency_fund_target,
        "baseline_health_score": base_health,
        "recommended_scenario": recommended.name,
        "income_shock": True,
    }

    return SimulationResult(
        scenarios=scenarios,
        timeline=recommended.timeline,
        alert=alert,
        subject=subject,
        facts=facts,
    )
