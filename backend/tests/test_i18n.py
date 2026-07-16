"""Arabic parity tests.

The contract for localisation is narrow and absolute: **the words change, the numbers do
not.** These tests run the same simulations in both languages and assert that every
computed figure is bit-for-bit identical, and that every user-visible string actually
changed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import i18n  # noqa: E402
from router import classify_fallback  # noqa: E402
from simulation import (  # noqa: E402
    baseline_timeline,
    health_breakdown,
    simulate_income_shock,
    simulate_purchase,
)
from twin_profile import load_profile  # noqa: E402

NUMERIC_FIELDS = [
    "remaining_savings",
    "monthly_cash_flow",
    "emergency_fund_months",
    "emergency_fund_ok",
    "risk",
    "goal_delay_months",
    "upfront_cost",
    "total_cost",
    "monthly_payment",
    "health_score",
    "health_delta",
    "recommended",
    "fidelity",
    "key",
]


@pytest.fixture(scope="module")
def profile():
    return load_profile()


def test_language_normalisation():
    assert i18n.normalize("ar") == "ar"
    assert i18n.normalize("AR-SA") == "ar"
    assert i18n.normalize("en-GB") == "en"
    # Anything unknown falls back to English rather than exploding.
    assert i18n.normalize("fr") == "en"
    assert i18n.normalize(None) == "en"
    assert i18n.normalize(123) == "en"
    assert i18n.is_rtl("ar") is True
    assert i18n.is_rtl("en") is False


def test_currency_keeps_latin_digits():
    assert i18n.sar(120_000, "en") == "120,000 SAR"
    assert i18n.sar(120_000, "ar") == "120,000 ⃁"


def test_missing_translation_falls_back_to_english():
    assert i18n.t("does.not.exist", "ar") == "does.not.exist"
    # A template with a missing variable degrades to the raw template, not a KeyError.
    assert "{" in i18n.t("rec.low", "en")


@pytest.mark.parametrize("price", [300, 120_000, 220_000, 800_000])
def test_purchase_numbers_are_identical_across_languages(profile, price):
    en = simulate_purchase(profile, item="car", price=price, lang="en")
    ar = simulate_purchase(profile, item="سيارة", price=price, lang="ar")

    assert len(en.scenarios) == len(ar.scenarios)

    for e, a in zip(en.scenarios, ar.scenarios):
        # Same scenario, same maths.
        assert e.key == a.key
        for field in NUMERIC_FIELDS:
            assert getattr(e, field) == getattr(a, field), f"{field} diverged on {e.key}"

        # ...and genuinely different words.
        assert e.name != a.name
        assert e.recommendation != a.recommendation

        # The projections must match month for month.
        assert len(e.timeline) == len(a.timeline)
        for me, ma in zip(e.timeline, a.timeline):
            assert (me.income, me.expenses, me.purchase, me.savings) == (
                ma.income, ma.expenses, ma.purchase, ma.savings
            )
            assert me.month != ma.month  # "Aug 2026" vs "أغسطس 2026"

    assert en.alert["level"] == ar.alert["level"]
    assert en.alert["message"] != ar.alert["message"]


def test_the_danger_alert_fires_in_arabic(profile):
    """The whole product is this moment. It has to work in both languages."""
    ar = simulate_purchase(profile, item="سيارة", price=220_000, lang="ar")
    assert ar.alert["level"] == "danger"
    assert "صندوق الطوارئ" in ar.alert["message"]
    assert "30,000 ⃁" in ar.alert["message"]

    buy = next(s for s in ar.scenarios if s.key == "buy_now")
    assert buy.remaining_savings == 30_000
    assert buy.risk == "high"
    # Safety still beats fidelity in Arabic.
    assert next(s for s in ar.scenarios if s.recommended).risk == "low"


def test_arabic_item_matches_an_english_goal(profile):
    """'سيارة' has to satisfy the profile's 'Buy a car' goal, via its Arabic label  
    otherwise the goal-delay maths would silently differ between languages."""
    en = simulate_purchase(profile, item="car", price=220_000, lang="en")
    ar = simulate_purchase(profile, item="سيارة", price=220_000, lang="ar")
    en_buy = next(s for s in en.scenarios if s.key == "buy_now")
    ar_buy = next(s for s in ar.scenarios if s.key == "buy_now")
    assert en_buy.goal_delay_months == ar_buy.goal_delay_months == 5
    assert en_buy.health_score == ar_buy.health_score


def test_recurring_and_income_shock_parity(profile):
    en = simulate_purchase(profile, item="subscription", price=300, recurring=True, lang="en")
    ar = simulate_purchase(profile, item="اشتراك", price=300, recurring=True, lang="ar")
    assert [s.key for s in en.scenarios] == [s.key for s in ar.scenarios]
    assert [s.monthly_cash_flow for s in en.scenarios] == [
        s.monthly_cash_flow for s in ar.scenarios
    ]

    en_shock = simulate_income_shock(profile, change_pct=-20, lang="en")
    ar_shock = simulate_income_shock(profile, change_pct=-20, lang="ar")
    assert [s.key for s in en_shock.scenarios] == [s.key for s in ar_shock.scenarios]
    assert en_shock.facts["new_salary"] == ar_shock.facts["new_salary"] == 14_400
    # "Clear the Loan" is still the right call in Arabic.
    assert next(s for s in ar_shock.scenarios if s.recommended).key == "clear_loan"


def test_profile_and_dashboard_localise(profile):
    ar = profile.to_dict("ar")
    assert ar["name"] == "سعد"
    assert ar["city"] == "الرياض"
    assert ar["goals"][0]["name"] == "شراء سيارة"
    assert ar["liabilities"][0]["name"] == "قرض شخصي"
    assert "الإيجار" in ar["expense_breakdown"]
    # Numbers untouched.
    assert ar["salary"] == 18_000
    assert ar["goals"][0]["amount"] == 120_000
    assert ar["expense_breakdown"]["الإيجار"] == 3_500

    health_en = health_breakdown(profile, "en")
    health_ar = health_breakdown(profile, "ar")
    assert health_en["score"] == health_ar["score"] == 99.0
    assert health_ar["label"] == "ممتاز"
    assert health_ar["components"][0]["name"] == "معدل الادخار"
    assert health_en["components"][0]["points"] == health_ar["components"][0]["points"]


def test_baseline_timeline_localises_months_not_money(profile):
    en = baseline_timeline(profile, lang="en")
    ar = baseline_timeline(profile, lang="ar")
    assert [r.savings for r in en] == [r.savings for r in ar]
    assert ar[0].month.split()[0] in i18n.MONTHS["ar"]
    assert "قرض شخصي" in ar[0].events[0]


# -- Arabic routing with no LLM at all --------------------------------------------------


def test_arabic_rule_based_routing():
    """With no Groq key, Arabic must still route and extract correctly."""
    car = classify_fallback("ماذا لو اشتريت سيارة بـ 120,000 ⃁؟", [])
    assert car["intent"] == "purchase_simulation"
    assert car["price"] == 120_000
    assert car["item"] == "سيارة"
    assert car["recurring"] is False
    assert "car" in car["topic_en"]

    thousands = classify_fallback("أريد شراء سيارة بـ 120 ألف", [])
    assert thousands["price"] == 120_000

    sub = classify_fallback("هل أقدر على اشتراك بـ 300 ⃁ شهريًا؟", [])
    assert sub["intent"] == "purchase_simulation"
    assert sub["price"] == 300
    assert sub["recurring"] is True

    shock = classify_fallback("ماذا يحدث إذا انخفض راتبي بنسبة 20%؟", [])
    assert shock["intent"] == "purchase_simulation"
    assert shock["income_change_pct"] == -20

    raise_ = classify_fallback("ماذا لو زاد راتبي 10%؟", [])
    assert raise_["income_change_pct"] == 10

    question = classify_fallback("كم يجب أن أحتفظ في صندوق الطوارئ؟", [])
    assert question["intent"] == "financial_question"
    assert "emergency" in question["topic_en"]

    hello = classify_fallback("مرحبا", [])
    assert hello["intent"] == "chitchat"


def test_arabic_followup_resolves_from_history():
    history = [{"role": "user", "content": "ماذا لو اشتريت سيارة بـ 120,000 ⃁؟"}]
    wait = classify_fallback("وماذا لو انتظرت ستة أشهر؟", history)
    assert wait["intent"] == "purchase_simulation"
    assert wait["price"] == 120_000
    assert wait["financing_option"] == "wait"
