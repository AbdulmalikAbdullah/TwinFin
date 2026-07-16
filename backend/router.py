"""Intent routing and answer generation.

Every chat message is classified before anything else happens:

    purchase_simulation -> extract {item, price, recurring, financing} -> run the
                           simulation engine -> retrieve RAG context -> write the answer
    financial_question  -> retrieve RAG context + the Twin profile -> write the answer
    chitchat            -> answer directly, briefly, no retrieval

Two rules hold throughout:

  1. **The LLM never does arithmetic.** It receives the engine's output as structured
     data and is instructed, explicitly, to reuse those figures verbatim.
  2. **Everything degrades.** If Groq is missing or down, a rule-based classifier and a
     template writer take over. The numbers are identical either way, because they never
     came from the model in the first place.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import i18n
import llm
import rag
from i18n import t
from simulation import (
    SimulationResult,
    simulate_income_shock,
    simulate_purchase,
)
from twin_profile import Profile

log = logging.getLogger(__name__)

PURCHASE = "purchase_simulation"
QUESTION = "financial_question"
CHITCHAT = "chitchat"

# What to tell the model about the language it must reply in. The *numbers* are already
# fixed by the engine; only the prose changes.
LANG_INSTRUCTION = {
    "en": "Write your answer in English.",
    "ar": (
        "اكتب إجابتك بالعربية الفصحى المبسطة، بنبرة ودّية ومباشرة. "
        "استخدم الأرقام اللاتينية (120,000) واكتب العملة هكذا: «120,000 ريال». "
        "لا تترجم أسماء ملفات المصادر — اتركها كما هي (مثل: emergency_fund.md)."
    ),
}


# -- Intent classification --------------------------------------------------------------

CLASSIFY_SYSTEM = """You are the intent router for Twin, a Saudi personal-finance assistant.

Classify the user's message and extract any purchase details. Reply with JSON only:

{
  "intent": "purchase_simulation" | "financial_question" | "chitchat",
  "item": string | null,            // what is being bought, 1-3 words, lowercase ("car", "iphone", "gym subscription")
  "price": number | null,           // amount in SAR, digits only. "120k" -> 120000
  "recurring": boolean,             // true if this is a per-month commitment, not a one-off
  "financing_option": string | null,// "cash" | "finance" | "wait" if the user named one
  "income_change_pct": number | null,// e.g. -20 for "what if my salary drops 20%"
  "topic_en": string                 // 3-8 ENGLISH keywords describing the topic, ALWAYS
                                     // in English even for Arabic messages. Used to search
                                     // an English knowledge base.
                                     // e.g. "buying a car cash vs murabaha financing"
}

Rules:
- purchase_simulation: the user is considering spending money, asking whether they can
  afford something, comparing paying cash vs financing, asking to delay a purchase, or
  asking what happens if their income changes. Anything with a price or an income change.
- financial_question: general advice with no specific transaction (zakat, budgeting,
  emergency funds, how murabaha works).
- chitchat: greetings, thanks, "who are you", small talk.
- Resolve references against the conversation history. If the user says "what if I wait
  six months?" and a 120000 SAR car was just discussed, return that item and price with
  financing_option "wait".
- "300 SAR per month" / "monthly subscription" -> recurring: true, price: 300.
- Never guess a price that was not stated or previously discussed. Use null.

The message may be in English or Arabic. Classify Arabic exactly the same way, and return
`item` in the SAME language the user wrote in ("سيارة" for an Arabic message, "car" for an
English one) — it is shown back to them. Prices are always plain digits: "120 ألف" -> 120000.
"""


def _history_text(history: list[dict[str, str]], limit: int = 6) -> str:
    if not history:
        return "(no prior messages)"
    lines = []
    for turn in history[-limit:]:
        role = turn.get("role", "user")
        content = str(turn.get("content", ""))[:400]
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


# Rule-based extraction, used when Groq is unavailable. Also used to sanity-check the LLM.
# Both languages are handled here, so the app keeps working in Arabic with no LLM at all.
_PRICE_PATTERNS = [
    # 120k / 1.5k  ·  120 ألف
    (re.compile(r"(\d+(?:\.\d+)?)\s*k\b", re.I), 1_000),
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:ألف|الف)"), 1_000),
    # 120,000 SAR / SAR 120000 / 120000 riyals / 120,000 ريال / ر.س 120000
    (re.compile(r"(?:sar|sr|riyals?|ريال|ر\.?س)\s*([\d,]+(?:\.\d+)?)", re.I), 1),
    (re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:sar|sr|riyals?|ريال|ر\.?س)", re.I), 1),
    # bare number, 3+ digits
    (re.compile(r"\b(\d{3,}(?:,\d{3})*(?:\.\d+)?)\b"), 1),
]

_RECURRING = re.compile(
    r"(?:/|per\s+|a\s+|each\s+|every\s+)month|monthly|subscription|per\s+year|annually"
    r"|شهري|شهريا|شهريًا|بالشهر|في\s*الشهر|كل\s*شهر|اشتراك|سنوي",
    re.I,
)
_PURCHASE_WORDS = re.compile(
    r"\b(buy|bought|buying|purchase|afford|cost|price|get\s+a|spend|finance|financing|"
    r"instal?lment|murabaha|loan\s+for|subscri|upgrade|wait)\b"
    r"|اشتري|أشتري|اشتريت|شريت|شراء|أشتريه|تكلفة|سعر|أقدر|اقدر|بكم|تمويل|مرابحة|قسط|"
    r"أقساط|اشتراك|انتظر|أنتظر",
    re.I,
)
_QUESTION_WORDS = re.compile(
    r"\b(zakat|budget|emergency|save|saving|invest|debt|advice|should\s+i|how\s+(?:do|much|many)|"
    r"what\s+is|explain|halal|riba|islamic|plan|retire|fund)\b"
    r"|زكاة|ميزانية|طوارئ|ادخار|ادّخار|استثمار|دين|ديون|نصيحة|كيف|ماهو|ما\s+هو|حلال|ربا|"
    r"إسلامي|تخطيط|تقاعد|صندوق",
    re.I,
)
_CHITCHAT = re.compile(
    r"^\s*(hi|hey|hello|salam|assalam|marhaba|thanks|thank\s+you|shukran|ok|okay|"
    r"who\s+are\s+you|what\s+are\s+you|bye|good\s+(morning|evening))\b"
    r"|^\s*(مرحبا|مرحبًا|السلام|أهلا|أهلًا|هلا|شكرا|شكرًا|من\s+أنت|مين\s+أنت|وداعا|صباح|مساء)",
    re.I,
)
_INCOME_CHANGE = re.compile(
    r"(?:salary|income|pay|wage)\D{0,30}?(drop|fall|cut|decrease|reduce|rise|increase|go\s+up|raise)"
    r"\D{0,20}?(\d+(?:\.\d+)?)\s*%|"
    r"(\d+(?:\.\d+)?)\s*%\D{0,30}?(?:salary|income|pay)\D{0,20}?"
    r"(drop|fall|cut|decrease|reduce|rise|increase)|"
    # Arabic: راتبي ينخفض 20%  /  انخفض راتبي بنسبة 20%  /  زاد راتبي 10%
    r"(?:راتب|دخل)\S*\D{0,30}?(انخفض|ينخفض|نزل|ينزل|قلّ|قل|تخفيض|زاد|يزيد|ارتفع|يرتفع|زيادة)"
    r"\D{0,25}?(\d+(?:\.\d+)?)\s*%|"
    r"(انخفض|ينخفض|نزل|ينزل|تخفيض|زاد|يزيد|ارتفع|يرتفع|زيادة)\D{0,30}?(?:راتب|دخل)"
    r"\S*\D{0,25}?(\d+(?:\.\d+)?)\s*%",
    re.I,
)
_WAIT = re.compile(r"\bwait|delay|postpone|hold\s+off|later\b|انتظر|أنتظر|أجّل|أجل|تأجيل|لاحقا", re.I)
_ITEM = re.compile(
    r"\b(?:buy|buying|purchase|afford|get)\s+(?:a|an|the)?\s*([a-z][a-z\s\-]{1,25}?)"
    r"\s*(?:for|at|costing|worth|priced|\?|$|,)",
    re.I,
)
# Arabic: "اشتريت سيارة" / "شراء سيارة" / "أشتري جوال" -> the noun that follows the verb.
_ITEM_AR = re.compile(
    r"(?:اشتري|أشتري|اشتريت|شريت|شراء|أشتريه|اقتني|أقتني)\s+(?:ال)?([؀-ۿ]{3,15})"
)

_NEGATIVE_WORDS = re.compile(r"drop|fall|cut|decrease|reduce|انخفض|ينخفض|نزل|ينزل|قلّ|قل|تخفيض", re.I)


def _extract_price(text: str) -> float | None:
    for pattern, multiplier in _PRICE_PATTERNS:
        match = pattern.search(text)
        if match:
            raw = match.group(1).replace(",", "")
            try:
                value = float(raw) * multiplier
            except ValueError:
                continue
            if value > 0:
                return value
    return None


def _extract_income_change(text: str) -> float | None:
    """'my salary drops 20%' -> -20.0 · 'انخفض راتبي 20%' -> -20.0 · 'a 10% raise' -> 10.0"""
    match = _INCOME_CHANGE.search(text)
    if not match:
        return None
    number = next(
        (g for g in match.groups() if g and re.fullmatch(r"\d+(?:\.\d+)?", g)), None
    )
    if number is None:
        return None
    pct = float(number)
    # A cut in either language makes the change negative; anything else is a raise.
    return -pct if _NEGATIVE_WORDS.search(match.group(0)) else pct


def _extract_item(text: str) -> str | None:
    match = _ITEM_AR.search(text)
    if match:
        return match.group(1).strip()

    match = _ITEM.search(text)
    if match:
        item = match.group(1).strip().lower()
        item = re.sub(r"\s+", " ", item)
        # Drop trailing filler the regex may have swept up.
        item = re.sub(r"\b(new|nice|good|second\s*hand|used)\b", "", item).strip()
        if item and item not in {"it", "this", "that", "one"}:
            return item

    if re.search(r"\bsubscription\b", text, re.I):
        return "subscription"
    if re.search(r"اشتراك", text):
        return "اشتراك"
    return None


# The knowledge base is written in English, and the local embedding model only speaks
# English. An Arabic question therefore has to be *searched* in English or it retrieves
# noise. The LLM router returns a `topic_en` for exactly this; when there is no LLM, this
# map does the same job well enough for the topics the knowledge base actually covers.
_AR_TOPIC_HINTS = {
    "سيارة": "car vehicle",
    "سياره": "car vehicle",
    "تمويل": "financing loan",
    "مرابحة": "murabaha islamic financing",
    "قسط": "installment financing",
    "أقساط": "installment financing",
    "قرض": "loan debt",
    "زكاة": "zakat",
    "طوارئ": "emergency fund",
    "ادخار": "saving savings",
    "ادّخار": "saving savings",
    "مدخرات": "savings",
    "ميزانية": "budgeting budget",
    "راتب": "salary income",
    "دخل": "income salary",
    "اشتراك": "subscription recurring cost",
    "استثمار": "investing investment",
    "دين": "debt",
    "ديون": "debt",
    "تقاعد": "retirement planning",
    "حلال": "islamic finance halal",
    "ربا": "riba interest islamic finance",
    "إسلامي": "islamic finance",
    "عمرة": "goal saving umrah",
    "هدف": "goal planning",
    "بيت": "home property",
    "شقة": "apartment property",
}


def _topic_hints_ar(text: str) -> str:
    """English search terms for an Arabic message, so RAG hits the right document."""
    hits = [en for ar, en in _AR_TOPIC_HINTS.items() if ar in text]
    return " ".join(dict.fromkeys(" ".join(hits).split()))


def classify_fallback(message: str, history: list[dict[str, str]]) -> dict[str, Any]:
    """Rule-based routing. Keeps the whole app working with no LLM at all."""
    slots: dict[str, Any] = {
        "intent": QUESTION,
        "item": None,
        "price": None,
        "recurring": False,
        "financing_option": None,
        "income_change_pct": None,
        "topic_en": _topic_hints_ar(message) or None,
    }

    if _CHITCHAT.match(message) and not _PURCHASE_WORDS.search(message):
        slots["intent"] = CHITCHAT
        return slots

    income_change = _extract_income_change(message)
    if income_change is not None:
        slots["intent"] = PURCHASE
        slots["income_change_pct"] = income_change
        return slots

    price = _extract_price(message)
    item = _extract_item(message)

    # "What if I wait six months?" carries no price - resolve it from the conversation.
    if price is None and _WAIT.search(message):
        previous = _last_purchase_from_history(history)
        if previous:
            slots.update(previous)
            slots["intent"] = PURCHASE
            slots["financing_option"] = "wait"
            return slots

    if price is not None:
        slots["intent"] = PURCHASE
        slots["price"] = price
        # Left as None if unnamed — the engine picks a language-appropriate noun.
        slots["item"] = item
        slots["recurring"] = bool(_RECURRING.search(message))
        if re.search(r"financ|instal?lment|murabaha|loan|تمويل|مرابحة|قسط|أقساط", message, re.I):
            slots["financing_option"] = "finance"
        elif _WAIT.search(message):
            slots["financing_option"] = "wait"
        return slots

    if _PURCHASE_WORDS.search(message) and not _QUESTION_WORDS.search(message):
        # Wants to buy something but named no price - we cannot simulate, so treat it as
        # a question and let the answer ask for the price.
        slots["intent"] = QUESTION
        return slots

    slots["intent"] = QUESTION
    return slots


def _last_purchase_from_history(history: list[dict[str, str]]) -> dict[str, Any] | None:
    """Find the most recent price the conversation discussed, for pronoun-ish follow-ups."""
    for turn in reversed(history or []):
        if turn.get("role") != "user":
            continue
        text = str(turn.get("content", ""))
        price = _extract_price(text)
        if price:
            return {
                "price": price,
                "item": _extract_item(text),
                "recurring": bool(_RECURRING.search(text)),
            }
    return None


def classify(message: str, history: list[dict[str, str]]) -> dict[str, Any]:
    """Classify + extract. LLM first, rules as the safety net."""
    fallback = classify_fallback(message, history)

    if not llm.is_configured():
        return fallback

    try:
        user_prompt = (
            f"Conversation so far:\n{_history_text(history)}\n\n"
            f"Message to classify:\n{message}"
        )
        result = llm.complete_json(CLASSIFY_SYSTEM, user_prompt)
    except llm.LLMUnavailable as exc:
        log.warning("Router LLM unavailable (%s); using rule-based routing.", exc)
        return fallback

    intent = result.get("intent")
    if intent not in {PURCHASE, QUESTION, CHITCHAT}:
        return fallback

    slots: dict[str, Any] = {
        "intent": intent,
        "item": result.get("item") or None,
        "price": _coerce_number(result.get("price")),
        "recurring": bool(result.get("recurring")),
        "financing_option": result.get("financing_option") or None,
        "income_change_pct": _coerce_number(result.get("income_change_pct")),
        "topic_en": (result.get("topic_en") or "").strip() or None,
    }

    # A purchase_simulation with nothing to simulate is not a purchase_simulation. Give
    # the rules a chance to rescue it (they resolve "wait six months" from history), and
    # otherwise demote it to a question so the user gets an answer instead of an error.
    if slots["intent"] == PURCHASE and not slots["price"] and slots["income_change_pct"] is None:
        if fallback["intent"] == PURCHASE:
            return fallback
        slots["intent"] = QUESTION

    return slots


def _coerce_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.\-]", "", value)
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None
    return None


# -- Answer generation ------------------------------------------------------------------

ANSWER_SYSTEM = """You are Twin, a Saudi personal-finance assistant. You speak to the user
directly, warmly, and without fluff, like a sharp friend who happens to be a financial
planner.

ABSOLUTE RULE - YOU DO NOT DO ARITHMETIC.
Every figure you need has already been computed by a deterministic simulation engine and
is given to you below. Quote those numbers exactly as provided. Never add, subtract,
multiply, round, or estimate. Never invent a number that is not in the data. If a figure
you want is not there, describe the situation without it.

How to write the answer:
- Open with the verdict in one sentence. Lead with the decision, not the preamble.
- Use the user's real figures from the data. Say "130,000 SAR", not "your savings".
- Compare the options briefly - the UI already renders the scenario cards, so do not list
  them all out mechanically. Explain the trade-off between the best two.
- If there is an alert, address it head-on. This is the most important part of the answer.
- Ground your advice in the knowledge base and cite the source filename inline, like this:
  (source: emergency_fund.md). Cite at least one source.
- Format as short markdown. Bold the key numbers. 120-180 words. No headings.
- Currency is SAR. Write amounts as "120,000 SAR".

LANGUAGE: {language}
"""


def _scenario_digest(result: SimulationResult) -> str:
    """The engine's output, rendered for the prompt. This is the only place the model gets
    numbers from."""
    lines = [f"SUBJECT: {result.subject}", ""]
    lines.append("SCENARIOS (computed by the engine - reuse these figures verbatim):")
    for s in result.scenarios:
        mark = "  <-- RECOMMENDED" if s.recommended else ""
        lines.append(
            f"- {s.name}{mark}\n"
            f"    remaining savings: {s.remaining_savings:,.0f} SAR\n"
            f"    monthly cash flow: {s.monthly_cash_flow:,.0f} SAR\n"
            f"    emergency fund: {s.emergency_fund_months} months "
            f"({'OK' if s.emergency_fund_ok else 'BELOW TARGET'})\n"
            f"    risk: {s.risk}\n"
            f"    goal delay: {s.goal_delay_months} months\n"
            f"    health score: {s.health_score}/100 (change: {s.health_delta:+})\n"
            f"    total cost: {s.total_cost:,.0f} SAR\n"
            f"    engine verdict: {s.recommendation}"
        )

    lines.append("")
    lines.append("KEY FIGURES:")
    for key, value in result.facts.items():
        if isinstance(value, dict):
            inner = ", ".join(f"{k}={v}" for k, v in value.items())
            lines.append(f"- {key}: {inner}")
        else:
            lines.append(f"- {key}: {value}")

    if result.alert:
        lines.append("")
        lines.append(
            f"ALERT ({result.alert['level'].upper()}): {result.alert['message']}"
        )
    return "\n".join(lines)


def _system(lang: str, extra: str = "") -> str:
    return ANSWER_SYSTEM.format(language=LANG_INSTRUCTION[lang]) + extra


def answer_purchase(
    profile: Profile,
    message: str,
    result: SimulationResult,
    passages: list[dict[str, Any]],
    history: list[dict[str, str]],
    lang: str = "en",
) -> str:
    user_prompt = (
        f"FINANCIAL TWIN (the user's profile):\n{profile.summary_for_llm()}\n\n"
        f"KNOWLEDGE BASE (retrieved passages - cite the source filenames):\n"
        f"{rag.format_context(passages)}\n\n"
        f"SIMULATION (deterministic - these numbers are correct, use them):\n"
        f"{_scenario_digest(result)}\n\n"
        f"CONVERSATION:\n{_history_text(history)}\n\n"
        f"USER'S QUESTION: {message}\n\n"
        f"Write {profile.name}'s answer."
    )
    try:
        return llm.complete(_system(lang), user_prompt, temperature=0.4).strip()
    except llm.LLMUnavailable as exc:
        log.warning("Answer LLM unavailable (%s); using the template writer.", exc)
        return template_purchase_answer(profile, result, passages, lang)


def template_purchase_answer(
    profile: Profile,
    result: SimulationResult,
    passages: list[dict[str, Any]],
    lang: str = "en",
) -> str:
    """Deterministic prose. Not as fluent as the model, but always correct and always
    available - which is what matters when the wifi dies on stage. Localised, so the
    fallback is not an English-only escape hatch."""
    best = next(s for s in result.scenarios if s.recommended)
    alert = result.alert
    lines: list[str] = []

    if alert and alert["level"] == "danger":
        lines.append(f"{t('tpl.careful', lang)} {alert['message']}")
    elif alert and alert["level"] == "warning":
        lines.append(f"{t('tpl.proceed', lang)} {alert['message']}")
    else:
        lines.append(f"{t('tpl.works', lang)} {alert['message'] if alert else ''}".strip())

    lines.append("")
    lines.append(
        t(
            "tpl.recommend",
            lang,
            name=best.name,
            detail=best.detail,
            savings=i18n.sar(best.remaining_savings, lang),
            cash=i18n.sar(best.monthly_cash_flow, lang),
            cover=best.emergency_fund_months,
            target=i18n.sar(profile.emergency_fund_target, lang),
            risk=t(f"risk.{best.risk}", lang),
        )
    )

    others = [s for s in result.scenarios if not s.recommended]
    if others:
        riskiest = max(others, key=lambda s: {"low": 0, "medium": 1, "high": 2}[s.risk])
        if riskiest.risk != "low":
            lines.append("")
            lines.append(
                t(
                    "tpl.worth_knowing",
                    lang,
                    name=riskiest.name,
                    risk=t(f"risk.{riskiest.risk}", lang),
                    recommendation=riskiest.recommendation,
                )
            )

    if best.goal_delay_months:
        lines.append("")
        lines.append(t("tpl.goal_delay", lang, months=best.goal_delay_months))

    if passages:
        lines.append("")
        lines.append(t("tpl.source", lang, source=passages[0]["source"]))

    return "\n".join(lines)


def answer_question(
    profile: Profile,
    message: str,
    passages: list[dict[str, Any]],
    history: list[dict[str, str]],
    lang: str = "en",
) -> str:
    system = _system(
        lang,
        "\nThere is no simulation for this message - it is a general question. Answer from "
        "the knowledge base and the user's profile. You may quote figures from the profile "
        "block verbatim, but do not compute new ones. If the user seems to be considering a "
        "purchase but gave no price, ask them for the price so you can simulate it.",
    )
    user_prompt = (
        f"FINANCIAL TWIN (the user's profile):\n{profile.summary_for_llm()}\n\n"
        f"KNOWLEDGE BASE (retrieved passages - cite the source filenames):\n"
        f"{rag.format_context(passages)}\n\n"
        f"CONVERSATION:\n{_history_text(history)}\n\n"
        f"USER'S QUESTION: {message}\n\n"
        f"Write {profile.name}'s answer."
    )
    try:
        return llm.complete(system, user_prompt, temperature=0.4).strip()
    except llm.LLMUnavailable as exc:
        log.warning("Answer LLM unavailable (%s); using the template writer.", exc)
        return template_question_answer(profile, passages, lang)


def template_question_answer(
    profile: Profile, passages: list[dict[str, Any]], lang: str = "en"
) -> str:
    if not passages:
        return t(
            "tpl.no_llm",
            lang,
            savings=i18n.sar(profile.savings, lang),
            surplus=i18n.sar(profile.monthly_surplus, lang),
            target=i18n.sar(profile.emergency_fund_target, lang),
        )
    top = passages[0]
    # The knowledge base is authored in English; in Arabic we still cite it, but we do not
    # paste an English wall of text into an Arabic answer.
    intro = t(
        "tpl.kb_intro",
        lang,
        savings=i18n.sar(profile.savings, lang),
        surplus=i18n.sar(profile.monthly_surplus, lang),
    )
    if lang == "ar":
        return f"{intro}\n\n{t('tpl.source', lang, source=top['source'])}"
    excerpt = top["content"][:600].rsplit(" ", 1)[0]
    return f"{intro}\n\n{excerpt}…\n\n{t('tpl.source', lang, source=top['source'])}"


CHITCHAT_SYSTEM = """You are Twin, a Saudi personal-finance assistant. Reply to small talk
in one or two warm sentences, then steer back to what you are for: simulating the future
impact of a purchase before it is made. Do not give financial advice here and do not use
numbers. No markdown headings.

LANGUAGE: {language}"""


def answer_chitchat(
    profile: Profile, message: str, history: list[dict[str, str]], lang: str = "en"
) -> str:
    try:
        return llm.complete(
            CHITCHAT_SYSTEM.format(language=LANG_INSTRUCTION[lang]),
            f"User said: {message}\n\nReply briefly.",
            temperature=0.7,
            max_tokens=150,
        ).strip()
    except llm.LLMUnavailable:
        return t("tpl.chitchat", lang, name=profile.label(profile.name, lang))


# -- The router -------------------------------------------------------------------------


def _retrieval_query(message: str, slots: dict[str, Any], subject: str, lang: str) -> str:
    """Build the query we actually search the knowledge base with.

    In English the raw message plus the simulated subject works well. In Arabic it does
    not — the corpus and the embedding model are both English — so we search with the
    English topic instead, falling back to the raw message if we somehow have neither.
    """
    topic = slots.get("topic_en") or ""
    if lang == "ar":
        return topic or message
    return f"{message} {subject} {topic}".strip()


def handle(
    profile: Profile,
    message: str,
    history: list[dict[str, str]] | None = None,
    lang: str = "en",
) -> dict[str, Any]:
    """Route one chat message end to end and return the API response body."""
    history = history or []
    lang = i18n.normalize(lang)
    slots = classify(message, history)
    intent = slots["intent"]

    if intent == CHITCHAT:
        return {
            "intent": CHITCHAT,
            "answer": answer_chitchat(profile, message, history, lang),
            "scenarios": [],
            "timeline": [],
            "alert": None,
            "sources": [],
        }

    if intent == PURCHASE:
        if slots["income_change_pct"] is not None:
            result = simulate_income_shock(
                profile, change_pct=slots["income_change_pct"], lang=lang
            )
        else:
            result = simulate_purchase(
                profile,
                item=slots["item"] or "",
                price=float(slots["price"]),
                recurring=bool(slots["recurring"]),
                financing_option=slots["financing_option"],
                lang=lang,
            )

        # Retrieve against the *subject*, not just the raw message: "what if I wait six
        # months?" is a bad retrieval query, "buying a car for 120,000 SAR" is a good one.
        passages = rag.retrieve(_retrieval_query(message, slots, result.subject, lang))
        answer = answer_purchase(profile, message, result, passages, history, lang)

        body = result.to_dict()
        return {
            "intent": PURCHASE,
            "answer": answer,
            "scenarios": body["scenarios"],
            "timeline": body["timeline"],
            "alert": body["alert"],
            "subject": body["subject"],
            "sources": _sources(passages),
        }

    passages = rag.retrieve(_retrieval_query(message, slots, "", lang))
    return {
        "intent": QUESTION,
        "answer": answer_question(profile, message, passages, history, lang),
        "scenarios": [],
        "timeline": [],
        "alert": None,
        "sources": _sources(passages),
    }


def _sources(passages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"source": p["source"], "title": p["title"], "score": p["score"]}
        for p in passages
    ]
