"""Pre-demo preflight.

Runs every question from the demo script through the real router - the same code path the
chat endpoint uses - and prints what the judges will see. Run this before you present:

    python backend/demo_check.py

It exits non-zero if anything is actually broken, so you find out here rather than on stage.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The Windows console defaults to cp1252, which cannot encode the em-dashes and curly
# quotes the answers use. Without this, those lines print as blanks or blow up.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

import llm  # noqa: E402
import rag  # noqa: E402
import router  # noqa: E402
from twin_profile import load_profile  # noqa: E402

CAR_QUESTION = "What if I buy a car for 120,000 SAR?"

# Each entry is (question, history). "What if I wait six months?" is a follow-up — it only
# means anything after the car has been discussed, so it gets that context, exactly as it
# would in the live demo.
DEMO_QUESTIONS: list[tuple[str, list[dict[str, str]]]] = [
    (CAR_QUESTION, []),
    ("What if I buy a car for 220,000 SAR?", []),
    ("Can I afford a 300 SAR/month subscription?", []),
    ("What if I wait six months?", [{"role": "user", "content": CAR_QUESTION}]),
    ("What happens if my salary drops 20%?", []),
    ("How much should I keep in my emergency fund?", []),
    ("Hey, who are you?", []),
]

RISK_COLOUR = {"low": "OK  ", "medium": "WARN", "high": "HIGH"}


def main() -> None:
    profile = load_profile()
    _, embed_backend = rag.get_embeddings()

    print()
    print("=" * 78)
    print("  TWIN — PREFLIGHT")
    print("=" * 78)
    print(f"  Twin        : {profile.name}, {profile.age}, {profile.city}")
    print(f"  Savings     : {profile.savings:,.0f} SAR")
    print(f"  Surplus     : {profile.monthly_surplus:,.0f} SAR/month")
    print(f"  EF target   : {profile.emergency_fund_target:,.0f} SAR")
    print(f"  LLM         : {'Groq — ' + str(llm.is_configured()) if llm.is_configured() else 'NOT CONFIGURED (deterministic fallback — numbers still correct)'}")
    print(f"  Embeddings  : {embed_backend}")
    print(f"  Ingested    : {rag.is_ingested()}")
    print("=" * 78)

    failures: list[str] = []

    for question, history in DEMO_QUESTIONS:
        print()
        print(f"> {question}")
        print("-" * 78)
        try:
            response = router.handle(profile, question, history)
        except Exception as exc:  # noqa: BLE001
            print(f"  !! CRASHED: {type(exc).__name__}: {exc}")
            failures.append(question)
            continue

        print(f"  intent  : {response['intent']}")
        if response.get("sources"):
            print(f"  sources : {', '.join(s['source'] for s in response['sources'])}")

        alert = response.get("alert")
        if alert:
            print(f"  ALERT   : [{alert['level'].upper()}] {alert['message']}")

        for s in response.get("scenarios") or []:
            star = "*" if s["recommended"] else " "
            print(
                f"  {star} {RISK_COLOUR[s['risk']]} {s['name']:<20} "
                f"savings {s['remaining_savings']:>10,.0f}  "
                f"cash/mo {s['monthly_cash_flow']:>8,.0f}  "
                f"EF {s['emergency_fund_months']:>5} mo  "
                f"delay {s['goal_delay_months']:>2} mo  "
                f"health {s['health_score']:>5} ({s['health_delta']:+})"
            )

        answer = (response.get("answer") or "").strip()
        print()
        for line in answer.splitlines():
            print(f"  | {line}")

        # Sanity gates. These are the acceptance criteria, checked automatically.
        if not answer:
            failures.append(f"{question}: empty answer")
        if response["intent"] == "purchase_simulation":
            if len(response["scenarios"]) < 3:
                failures.append(f"{question}: too few scenarios")
            if not response["timeline"]:
                failures.append(f"{question}: no timeline")
            if not response["sources"]:
                failures.append(f"{question}: no knowledge-base citation")

    print()
    print("=" * 78)
    if failures:
        print("  FAILURES:")
        for f in failures:
            print(f"   - {f}")
        sys.exit(1)
    print("  All demo questions answered. You're good to go.")
    print("=" * 78)
    print()


if __name__ == "__main__":
    main()
