"""Unit tests for the deterministic simulation engine.

Every expected value here is worked out by hand from data/financial_twin.md, which is the
whole point: if the LLM were doing the arithmetic these tests could not exist.

Baseline profile:
    salary            18,000 SAR/month
    expenses           9,000 SAR/month
    loan               1,200 SAR/month (18 months left)
    savings          250,000 SAR
    surplus           18,000 - 9,000 - 1,200 = 7,800 SAR/month
    emergency target   6 x 9,000 = 54,000 SAR
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import EMERGENCY_FUND_MONTHS  # noqa: E402
from twin_profile import load_profile  # noqa: E402
from simulation import (  # noqa: E402
    baseline_timeline,
    conventional_loan,
    emergency_fund_months,
    health_score,
    months_to_afford,
    murabaha,
    risk_level,
    simulate_income_shock,
    simulate_purchase,
    zakat_due,
)


@pytest.fixture(scope="module")
def profile():
    return load_profile()


# -- Profile parsing -------------------------------------------------------------------


def test_profile_parses_from_markdown(profile):
    assert profile.name == "Saad"
    assert profile.age == 28
    assert profile.city == "Riyadh"
    assert profile.salary == 18_000
    assert profile.savings == 250_000
    assert profile.monthly_expenses == 9_000
    assert profile.risk_tolerance == "moderate"


def test_expense_breakdown_reconciles(profile):
    assert sum(profile.expense_breakdown.values()) == profile.monthly_expenses
    assert profile.expense_breakdown["rent"] == 3_500


def test_liabilities_and_goals(profile):
    assert len(profile.liabilities) == 1
    loan = profile.liabilities[0]
    assert loan.monthly_payment == 1_200
    assert loan.months_remaining == 18

    assert len(profile.goals) == 2
    car = profile.goals[0]
    assert car.amount == 120_000
    assert car.horizon_months == 12
    assert profile.goals[1].amount == 8_000


def test_derived_figures(profile):
    # 18,000 - 9,000 - 1,200
    assert profile.monthly_surplus == 7_800
    # 6 x 9,000
    assert profile.emergency_fund_target == 54_000
    assert profile.assets["Investment account"] == 40_000
    assert profile.zakatable_wealth == 290_000


# -- Financial primitives --------------------------------------------------------------


def test_emergency_fund_months():
    assert emergency_fund_months(130_000, 9_000) == 14.4  # matches the spec's example
    assert emergency_fund_months(54_000, 9_000) == 6.0
    assert emergency_fund_months(0, 9_000) == 0.0


def test_risk_rules():
    # Savings below the 54,000 emergency floor -> high, no matter how good cash flow is.
    assert risk_level(
        savings_after=30_000, cash_flow=7_800, salary=18_000, emergency_target=54_000
    ) == "high"
    # Cash flow under 10% of salary (1,800) -> high.
    assert risk_level(
        savings_after=250_000, cash_flow=1_383, salary=18_000, emergency_target=54_000
    ) == "high"
    # Between 1x and 1.5x the emergency target (54,000..81,000) -> medium.
    assert risk_level(
        savings_after=76_800, cash_flow=7_800, salary=18_000, emergency_target=54_000
    ) == "medium"
    # Cash flow under 25% of salary (4,500) -> medium.
    assert risk_level(
        savings_after=250_000, cash_flow=4_300, salary=18_000, emergency_target=54_000
    ) == "medium"
    assert risk_level(
        savings_after=130_000, cash_flow=7_800, salary=18_000, emergency_target=54_000
    ) == "low"


def test_murabaha_matches_hand_calculation():
    # 120,000 x 5% = 6,000 profit -> 126,000 total -> 126,000 / 36 = 3,500/month
    plan = murabaha(120_000)
    assert plan["profit"] == 6_000
    assert plan["total"] == 126_000
    assert plan["monthly"] == 3_500
    assert plan["term"] == 36


def test_conventional_loan_is_amortised():
    # Standard amortisation, 5.5% APR over 36 months on 120,000 SAR.
    loan = conventional_loan(120_000)
    assert loan["monthly"] == pytest.approx(3_623, abs=2)
    assert loan["total"] == pytest.approx(130_442, abs=50)
    # It must cost more than the murabaha for these inputs - that is the teaching point.
    assert loan["total"] > murabaha(120_000)["total"]


def test_months_to_afford():
    # Needs 8,000 + 54,000 = 62,000; has 30,000; 32,000 short at 7,800/month -> ceil(4.10) = 5
    assert months_to_afford(
        savings=30_000, target_amount=8_000, emergency_target=54_000, surplus=7_800
    ) == 5
    # Already affordable without touching the buffer.
    assert months_to_afford(
        savings=250_000, target_amount=8_000, emergency_target=54_000, surplus=7_800
    ) == 0


def test_zakat_and_the_effect_of_a_purchase(profile):
    # 2.5% of (250,000 cash + 40,000 investments)
    assert zakat_due(profile.zakatable_wealth) == 7_250
    # Buying a 120,000 car converts cash into an exempt personal-use asset.
    assert zakat_due(profile.zakatable_wealth - 120_000) == 4_250


def test_health_score_components(profile):
    """Baseline: 40 (savings rate) + 30 (EF) + 19.05 (DTI) + 10 (goal) = 99.05"""
    score = health_score(
        salary=18_000,
        monthly_expenses=9_000,
        monthly_debt=1_200,
        savings=250_000,
        goal_amount=120_000,
        emergency_target=54_000,
    )
    assert score == pytest.approx(99.0, abs=0.1)

    # A broken emergency fund must visibly hurt: 30,000 / 54,000 = 55.6% of the EF points,
    # and goal progress collapses to zero because savings are under the floor.
    hurt = health_score(
        salary=18_000,
        monthly_expenses=9_000,
        monthly_debt=1_200,
        savings=30_000,
        goal_amount=120_000,
        emergency_target=54_000,
    )
    assert hurt == pytest.approx(75.7, abs=0.2)
    assert hurt < score


def test_health_score_is_bounded():
    assert health_score(
        salary=18_000, monthly_expenses=17_500, monthly_debt=8_000,
        savings=0, goal_amount=120_000, emergency_target=105_000,
    ) == 0.0
    assert health_score(
        salary=18_000, monthly_expenses=5_000, monthly_debt=0,
        savings=1_000_000, goal_amount=10_000, emergency_target=30_000,
    ) == 100.0


# -- Baseline timeline -----------------------------------------------------------------


def test_baseline_timeline_reconciles(profile):
    rows = baseline_timeline(profile)
    assert len(rows) == 12

    # Month 1: 250,000 + 18,000 - (9,000 + 1,200) = 257,800
    assert rows[0].savings == 257_800
    assert rows[0].income == 18_000
    assert rows[0].expenses == 10_200  # living costs + debt service

    # The loan has 18 months left, so it never clears inside a 12-month window.
    assert all(row.expenses == 10_200 for row in rows)
    # 250,000 + 12 x 7,800 = 343,600
    assert rows[-1].savings == 343_600
    assert not any(row.warnings for row in rows)

    # The ledger must reconcile exactly, month over month.
    previous = profile.savings
    for row in rows:
        assert row.savings == pytest.approx(
            previous + row.income - row.expenses - row.purchase
        )
        previous = row.savings


def test_loan_payoff_frees_cash_flow(profile):
    """If the loan ends inside the window, the engine must stop charging for it."""
    from dataclasses import replace

    from twin_profile import Liability

    short = replace(
        profile, liabilities=[Liability("Personal loan", 1_200, 3)]
    )
    rows = baseline_timeline(short)
    assert rows[2].expenses == 10_200  # month 3: last payment
    assert any("cleared" in e for e in rows[2].events)
    assert rows[3].expenses == 9_000  # month 4: the 1,200 is yours again


# -- The headline demo: a 120,000 SAR car ----------------------------------------------


def test_car_120k_scenarios_are_hand_verifiable(profile):
    result = simulate_purchase(profile, item="car", price=120_000)
    cards = {s.name: s for s in result.scenarios}
    assert set(cards) == {
        "Buy Now",
        "Wait 6 Months",
        "Finance (Murabaha)",
        "Cheaper Alternative",
    }

    # BUY NOW: 250,000 - 120,000 = 130,000 left. Cash flow unchanged at 7,800.
    # 130,000 / 9,000 = 14.4 months of cover. (These are the spec's own example numbers.)
    buy = cards["Buy Now"]
    assert buy.remaining_savings == 130_000
    assert buy.monthly_cash_flow == 7_800
    assert buy.emergency_fund_months == 14.4
    assert buy.emergency_fund_ok is True
    assert buy.risk == "low"
    assert buy.goal_delay_months == 0
    assert buy.total_cost == 120_000

    # WAIT 6 MONTHS: 250,000 + 6 x 7,800 = 296,800, then - 120,000 = 176,800.
    wait = cards["Wait 6 Months"]
    assert wait.remaining_savings == 176_800
    assert wait.goal_delay_months == 6  # the car itself arrives six months later
    assert wait.risk == "low"

    # FINANCE: savings untouched; 3,500/month installment cuts cash flow to 4,300,
    # which is under 25% of an 18,000 salary -> medium risk.
    fin = cards["Finance (Murabaha)"]
    assert fin.remaining_savings == 250_000
    assert fin.monthly_payment == 3_500
    assert fin.monthly_cash_flow == 4_300
    assert fin.total_cost == 126_000
    assert fin.risk == "medium"

    # CHEAPER: 65% of 120,000 = 78,000 -> 172,000 left.
    cheap = cards["Cheaper Alternative"]
    assert cheap.upfront_cost == 78_000
    assert cheap.remaining_savings == 172_000
    assert cheap.risk == "low"

    # Saad can afford this outright, so the Twin should say so rather than nudging him
    # into a compromise he does not need.
    assert buy.recommended is True
    assert result.alert["level"] == "info"


def test_car_120k_timeline_is_consistent(profile):
    result = simulate_purchase(profile, item="car", price=120_000)
    rows = result.timeline  # the recommended (Buy Now) projection
    assert len(rows) == 12
    # Month 1: 250,000 + 18,000 - 10,200 - 120,000 = 137,800
    assert rows[0].savings == 137_800
    assert rows[0].purchase == 120_000
    assert any("car" in e.lower() for e in rows[0].events)
    # Never breaches the emergency fund.
    assert not any(row.warnings for row in rows)


# -- The "Twin protects you" moment: a 220,000 SAR car ---------------------------------


def test_car_220k_breaks_the_emergency_fund_and_alerts(profile):
    result = simulate_purchase(profile, item="car", price=220_000)
    cards = {s.name: s for s in result.scenarios}

    # BUY NOW: 250,000 - 220,000 = 30,000, which is below the 54,000 floor.
    buy = cards["Buy Now"]
    assert buy.remaining_savings == 30_000
    assert buy.emergency_fund_ok is False
    assert buy.emergency_fund_months == 3.3
    assert buy.risk == "high"
    # Knock-on: the 8,000 Umrah goal now needs 62,000 total; he is 32,000 short at
    # 7,800/month -> 5 months of delay.
    assert buy.goal_delay_months == 5

    # FINANCE: 220,000 x 1.05 / 36 = 6,416.67/month -> cash flow 7,800 - 6,416.67 = 1,383.33,
    # under 10% of salary (1,800) -> high risk.
    fin = cards["Finance (Murabaha)"]
    assert fin.monthly_payment == pytest.approx(6_416.67, abs=0.01)
    assert fin.monthly_cash_flow == pytest.approx(1_383.33, abs=0.01)
    assert fin.risk == "high"

    # The alert must fire, and it must be the loud one.
    assert result.alert is not None
    assert result.alert["level"] == "danger"
    assert "emergency fund" in result.alert["message"].lower()

    # Safety beats fidelity: the Twin must not recommend a high-risk option when a
    # low-risk one exists.
    recommended = next(s for s in result.scenarios if s.recommended)
    assert recommended.risk == "low"
    assert recommended.name == "Cheaper Alternative"

    # And the health score has to move enough for the gauge to tell the story.
    # Buy Now: 40 (savings rate, unchanged) + 16.7 (EF: only 30,000 of a 54,000 target)
    #        + 19.05 (DTI, unchanged) + 10 (the car goal is actually achieved) = 85.7,
    # down from 99.05.
    assert buy.health_score == pytest.approx(85.7, abs=0.2)
    assert buy.health_delta == pytest.approx(-13.3, abs=0.2)
    # Financing is far worse: the 6,416.67/month installment pushes debt-to-income to
    # 42% (zero points) and craters the savings rate. 15.4 + 30 + 0 + 10 = 55.4.
    assert fin.health_score == pytest.approx(55.4, abs=0.2)
    assert fin.health_delta < -40


def test_purchase_larger_than_savings(profile):
    result = simulate_purchase(profile, item="apartment", price=800_000)
    buy = next(s for s in result.scenarios if s.name == "Buy Now")
    assert buy.remaining_savings == -550_000
    assert result.alert["level"] == "danger"
    assert "cannot pay" in result.alert["message"].lower()


# -- Recurring commitments -------------------------------------------------------------


def test_recurring_subscription(profile):
    result = simulate_purchase(profile, item="subscription", price=300, recurring=True)
    cards = {s.name: s for s in result.scenarios}
    assert set(cards) == {"Subscribe Now", "Pay Annually", "Cheaper Tier", "Skip It"}

    # A subscription does not dent savings; it narrows cash flow, permanently.
    sub = cards["Subscribe Now"]
    assert sub.remaining_savings == 250_000
    assert sub.monthly_cash_flow == 7_500  # 7,800 - 300
    assert sub.total_cost == 3_600  # a year of it
    assert sub.risk == "low"
    assert sub.recommended is True

    # Emergency-fund cover falls slightly because the target rises with expenses:
    # 250,000 / 9,300 = 26.9 months.
    assert sub.emergency_fund_months == 26.9
    assert result.facts["pct_of_surplus"] == pytest.approx(3.8, abs=0.1)


def test_unaffordable_subscription_is_flagged(profile):
    # 7,500/month of new commitments against a 7,800 surplus leaves 300/month.
    result = simulate_purchase(profile, item="villa rental", price=7_500, recurring=True)
    sub = next(s for s in result.scenarios if s.name == "Subscribe Now")
    assert sub.monthly_cash_flow == 300
    assert sub.risk == "high"
    assert result.alert["level"] == "danger"


# -- Income shock ----------------------------------------------------------------------


def test_salary_drop_20_percent(profile):
    result = simulate_income_shock(profile, change_pct=-20)
    cards = {s.name: s for s in result.scenarios}
    assert set(cards) == {"Absorb It", "Trim Spending 15%", "Clear the Loan"}

    # 18,000 x 0.8 = 14,400. Surplus: 14,400 - 9,000 - 1,200 = 4,200.
    absorb = cards["Absorb It"]
    assert absorb.monthly_cash_flow == 4_200
    assert absorb.remaining_savings == 250_000
    assert absorb.emergency_fund_ok is True

    # Trimming 15% of a 9,000 budget -> 7,650 expenses -> 14,400 - 7,650 - 1,200 = 5,550.
    trim = cards["Trim Spending 15%"]
    assert trim.monthly_cash_flow == 5_550

    # Clearing the loan costs 1,200 x 18 = 21,600 and permanently frees 1,200/month:
    # 14,400 - 9,000 - 0 = 5,400, with 228,400 left in the bank.
    clear = cards["Clear the Loan"]
    assert clear.upfront_cost == 21_600
    assert clear.remaining_savings == 228_400
    assert clear.monthly_cash_flow == 5_400
    assert clear.health_score > absorb.health_score  # no debt = a better position

    # For an income shock there is no "thing the user asked for", so the ranking falls
    # through to the health score. The Twin should recommend the genuinely best move
    # rather than defaulting to inertia — clearing the loan lands him at 100/100.
    assert clear.recommended is True
    assert clear.health_score == 100.0

    assert result.facts["new_salary"] == 14_400
    assert all(s.risk in {"low", "medium"} for s in result.scenarios)


def test_catastrophic_salary_drop_alerts(profile):
    # 18,000 x 0.4 = 7,200, which does not even cover 9,000 of expenses + 1,200 of debt.
    result = simulate_income_shock(profile, change_pct=-60)
    absorb = next(s for s in result.scenarios if s.name == "Absorb It")
    assert absorb.monthly_cash_flow == -3_000  # burning savings every month
    assert absorb.risk == "high"
    assert result.alert["level"] == "danger"
    # The projection has to show the bleed.
    assert absorb.timeline[-1].savings < profile.savings


# -- Invariants that must hold for any input -------------------------------------------


@pytest.mark.parametrize("price", [500, 5_000, 50_000, 120_000, 220_000, 400_000])
def test_invariants_hold_across_prices(profile, price):
    result = simulate_purchase(profile, item="car", price=price)

    assert len(result.scenarios) == 4
    assert sum(s.recommended for s in result.scenarios) == 1
    assert result.alert is not None
    assert 0 <= min(s.health_score for s in result.scenarios)
    assert max(s.health_score for s in result.scenarios) <= 100

    for s in result.scenarios:
        assert s.risk in {"low", "medium", "high"}
        assert s.recommendation  # every card carries a verdict
        assert len(s.timeline) == 12
        assert s.goal_delay_months >= 0
        # emergency_fund_ok must agree with the arithmetic behind it.
        assert s.emergency_fund_ok == (s.remaining_savings >= profile.emergency_fund_target)

        # Every projection must be an exactly reconciling ledger.
        previous = profile.savings if s.name != "Wait 6 Months" else profile.savings
        for row in s.timeline:
            assert row.savings == pytest.approx(
                previous + row.income - row.expenses - row.purchase, abs=0.01
            )
            previous = row.savings

    # A recommendation must never be riskier than an available alternative.
    best = next(s for s in result.scenarios if s.recommended)
    assert all(
        {"low": 0, "medium": 1, "high": 2}[best.risk]
        <= {"low": 0, "medium": 1, "high": 2}[s.risk]
        for s in result.scenarios
    )


def test_emergency_fund_target_is_six_months(profile):
    assert profile.emergency_fund_target == profile.monthly_expenses * EMERGENCY_FUND_MONTHS
