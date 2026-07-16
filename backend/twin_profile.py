"""Parses the Financial Twin profile from data/financial_twin.md.

The profile is authored as a YAML block inside a Markdown file so that it stays
human-editable (and demo-editable) without touching code. This module turns it into a
plain dataclass that the simulation engine can rely on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import EMERGENCY_FUND_MONTHS, PROFILE_PATH


@dataclass(frozen=True)
class Goal:
    """A named savings goal with a target amount and (optionally) a deadline."""

    name: str
    amount: float
    horizon_months: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "amount": self.amount,
            "horizon_months": self.horizon_months,
        }


@dataclass(frozen=True)
class Liability:
    """A recurring debt obligation."""

    name: str
    monthly_payment: float
    months_remaining: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "monthly_payment": self.monthly_payment,
            "months_remaining": self.months_remaining,
        }


@dataclass(frozen=True)
class Profile:
    """The user's Financial Twin: everything the engine needs, and nothing it doesn't."""

    name: str
    age: int
    city: str
    salary: float
    savings: float
    monthly_expenses: float
    expense_breakdown: dict[str, float] = field(default_factory=dict)
    assets: dict[str, float] = field(default_factory=dict)
    liabilities: list[Liability] = field(default_factory=list)
    goals: list[Goal] = field(default_factory=list)
    risk_tolerance: str = "moderate"
    # Display-only translations of the labels above (goal names, expense categories, …).
    # Deliberately holds no numbers: every figure has one source of truth.
    ar_labels: dict[str, str] = field(default_factory=dict)

    # -- Localisation ------------------------------------------------------------------

    def label(self, text: str, lang: str = "en") -> str:
        """Translate a label from the profile. Untranslated labels pass through unchanged,
        so a missing entry degrades to English rather than breaking the page."""
        if lang == "ar":
            return self.ar_labels.get(text, text)
        return text

    # -- Derived figures ---------------------------------------------------------------

    @property
    def monthly_debt(self) -> float:
        """Total monthly debt service across all liabilities."""
        return sum(item.monthly_payment for item in self.liabilities)

    @property
    def monthly_surplus(self) -> float:
        """Cash left over each month: salary - living expenses - debt payments."""
        return self.salary - self.monthly_expenses - self.monthly_debt

    @property
    def emergency_fund_target(self) -> float:
        """The floor: six months of essential expenses."""
        return self.monthly_expenses * EMERGENCY_FUND_MONTHS

    @property
    def primary_goal(self) -> Goal | None:
        """The first goal listed is treated as the primary one."""
        return self.goals[0] if self.goals else None

    @property
    def total_assets(self) -> float:
        return sum(self.assets.values())

    @property
    def zakatable_wealth(self) -> float:
        """Cash plus investable assets. Personal-use assets are exempt from zakat."""
        return self.savings + self.total_assets

    def to_dict(self, lang: str = "en") -> dict[str, Any]:
        """The profile as the API returns it. Every human-readable label is localised;
        every number is untouched."""
        tr = lambda text: self.label(text, lang)  # noqa: E731
        return {
            "name": tr(self.name),
            "age": self.age,
            "city": tr(self.city),
            "salary": self.salary,
            "savings": self.savings,
            "monthly_expenses": self.monthly_expenses,
            "expense_breakdown": {
                tr(k): v for k, v in self.expense_breakdown.items()
            },
            "assets": {tr(k): v for k, v in self.assets.items()},
            "liabilities": [
                {**item.to_dict(), "name": tr(item.name)} for item in self.liabilities
            ],
            "goals": [{**goal.to_dict(), "name": tr(goal.name)} for goal in self.goals],
            "risk_tolerance": tr(self.risk_tolerance),
            "monthly_debt": self.monthly_debt,
            "monthly_surplus": self.monthly_surplus,
            "emergency_fund_target": self.emergency_fund_target,
            "total_assets": self.total_assets,
        }

    def summary_for_llm(self) -> str:
        """A compact, token-cheap rendering of the Twin for the LLM prompt."""
        goals = "; ".join(
            f"{g.name} ({g.amount:,.0f} SAR"
            + (f" within {g.horizon_months} months)" if g.horizon_months else ")")
            for g in self.goals
        )
        debts = "; ".join(
            f"{d.name}: {d.monthly_payment:,.0f} SAR/month, {d.months_remaining} months left"
            for d in self.liabilities
        ) or "none"
        return (
            f"Name: {self.name}, age {self.age}, {self.city}\n"
            f"Salary: {self.salary:,.0f} SAR/month\n"
            f"Liquid savings: {self.savings:,.0f} SAR\n"
            f"Monthly expenses: {self.monthly_expenses:,.0f} SAR\n"
            f"Debt payments: {debts}\n"
            f"Monthly surplus: {self.monthly_surplus:,.0f} SAR\n"
            f"Emergency fund target: {self.emergency_fund_target:,.0f} SAR "
            f"({EMERGENCY_FUND_MONTHS} months of expenses)\n"
            f"Goals: {goals}\n"
            f"Risk tolerance: {self.risk_tolerance}"
        )


# -- Parsing --------------------------------------------------------------------------

_NUMBER = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def _first_number(text: str) -> float:
    """Pull the first number out of a string, tolerating thousands separators."""
    match = _NUMBER.search(text.replace(" ", ""))
    if not match:
        raise ValueError(f"no number found in {text!r}")
    return float(match.group().replace(",", ""))


def _parse_liability(text: str) -> Liability:
    """'Personal loan: 1200 SAR/month, 18 months remaining' -> Liability."""
    name, _, rest = text.partition(":")
    numbers = [float(n.replace(",", "")) for n in _NUMBER.findall(rest)]
    payment = numbers[0] if numbers else 0.0
    months = int(numbers[1]) if len(numbers) > 1 else 0
    return Liability(name=name.strip(), monthly_payment=payment, months_remaining=months)


def _parse_goal(text: str) -> Goal:
    """'Buy a car (~120000 SAR) within 12 months' -> Goal."""
    amounts = [float(n.replace(",", "")) for n in _NUMBER.findall(text)]
    horizon = None
    horizon_match = re.search(r"within\s+(\d+)\s+month", text, re.IGNORECASE)
    if horizon_match:
        horizon = int(horizon_match.group(1))
        # The horizon is also a number in the string; drop it from the amount candidates.
        amounts = [a for a in amounts if a != float(horizon)] or amounts
    amount = max(amounts) if amounts else 0.0
    # Strip the parenthetical amount and the trailing horizon from the display name.
    name = re.sub(r"\(.*?\)", "", text)
    name = re.sub(r"within\s+\d+\s+months?", "", name, flags=re.IGNORECASE)
    name = name.replace(":", "").strip(" ,-")
    name = re.sub(r"\s+\d[\d,]*\.?\d*\s*(SAR)?\s*$", "", name).strip()
    return Goal(name=name, amount=amount, horizon_months=horizon)


def _parse_asset(text: str) -> tuple[str, float]:
    """'Investment account: 40000 SAR' -> ('Investment account', 40000.0)."""
    name, _, rest = text.partition(":")
    return name.strip(), _first_number(rest)


def load_profile(path: Path | None = None) -> Profile:
    """Read and parse the Financial Twin markdown file.

    The parser is intentionally forgiving: it walks the YAML-ish block line by line and
    tracks the current list/mapping key by indentation. This keeps the profile file
    friendly to non-programmers without pulling in a YAML dependency.
    """
    path = path or PROFILE_PATH
    raw = path.read_text(encoding="utf-8")

    # Take the first fenced code block; fall back to the whole file if there isn't one.
    fence = re.search(r"```(?:yaml|yml)?\s*\n(.*?)```", raw, re.DOTALL)
    block = fence.group(1) if fence else raw

    scalars: dict[str, str] = {}
    expense_breakdown: dict[str, float] = {}
    ar_labels: dict[str, str] = {}
    assets: dict[str, float] = {}
    liabilities: list[Liability] = []
    goals: list[Goal] = []
    section: str | None = None

    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        indented = line[0] in " \t"
        stripped = line.strip()

        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if section == "assets":
                key, value = _parse_asset(item)
                assets[key] = value
            elif section == "liabilities":
                liabilities.append(_parse_liability(item))
            elif section == "goals":
                goals.append(_parse_goal(item))
            continue

        key, sep, value = stripped.partition(":")
        if not sep:
            continue
        key, value = key.strip(), value.strip()

        if indented and section == "expense_breakdown":
            expense_breakdown[key] = _first_number(value)
            continue

        # Translation blocks hold text, not numbers.
        if indented and section == "ar_labels":
            ar_labels[key] = value
            continue

        if value:
            scalars[key] = value
            section = None
        else:
            section = key  # a bare "key:" opens a list/mapping section

    profile = Profile(
        name=scalars.get("name", "User"),
        age=int(_first_number(scalars.get("age", "0"))),
        city=scalars.get("city", ""),
        salary=_first_number(scalars["salary"]),
        savings=_first_number(scalars["savings"]),
        monthly_expenses=_first_number(scalars["monthly_expenses"]),
        expense_breakdown=expense_breakdown,
        assets=assets,
        liabilities=liabilities,
        goals=goals,
        risk_tolerance=scalars.get("risk_tolerance", "moderate"),
        ar_labels=ar_labels,
    )

    # Sanity check: the breakdown should reconcile with the headline expense figure.
    if expense_breakdown:
        total = sum(expense_breakdown.values())
        if abs(total - profile.monthly_expenses) > 1:
            raise ValueError(
                f"expense_breakdown sums to {total:,.0f} but monthly_expenses is "
                f"{profile.monthly_expenses:,.0f} - fix data/financial_twin.md"
            )

    return profile
