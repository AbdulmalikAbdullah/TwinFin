"""Localization for everything the engine says out loud.

Twin's simulation engine does not only compute numbers — it also writes the scenario
names, the one-line verdicts, the alert messages and the timeline events. All of that is
deterministic prose, so all of it has to be translated here rather than left to the LLM.

Two rules:

  1. **Numbers never change.** Only their wrapper does: `120,000 SAR` / `120,000 ريال`.
     Latin digits are kept in Arabic — that is what Saudi banking apps do, and it keeps
     the figures verifiable against the English output at a glance.
  2. **Scenario identity is never translated.** Every scenario carries a stable `key`
     ("buy_now", "finance", …) that the ranking logic uses. `name` is display only.
"""

from __future__ import annotations

from datetime import date
from typing import Any

LANGS = ("en", "ar")
DEFAULT_LANG = "en"

# Right-to-left languages. Drives `dir="rtl"` on the frontend.
RTL_LANGS = ("ar",)


def normalize(lang: Any) -> str:
    """Coerce anything to a supported language code. Unknown input falls back to English."""
    if isinstance(lang, str) and lang.strip().lower()[:2] in LANGS:
        return lang.strip().lower()[:2]
    return DEFAULT_LANG


def is_rtl(lang: str) -> bool:
    return normalize(lang) in RTL_LANGS


# -- Numbers and dates ------------------------------------------------------------------

CURRENCY = {"en": "{amount} SAR", "ar": "{amount} ريال"}

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
           "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
}


def sar(amount: float, lang: str = DEFAULT_LANG) -> str:
    """Format a riyal amount. Latin digits in both languages — see the module docstring."""
    return CURRENCY[normalize(lang)].format(amount=f"{amount:,.0f}")


def month_label(offset: int, lang: str = DEFAULT_LANG, start: date | None = None) -> str:
    """Label for the month `offset` months from today. offset=1 -> next month."""
    start = start or date.today()
    index = start.month - 1 + offset
    year = start.year + index // 12
    month = index % 12
    return f"{MONTHS[normalize(lang)][month]} {year}"


def sentence_case(text: str, lang: str = DEFAULT_LANG) -> str:
    """Uppercase the first letter. A no-op in Arabic, which has no letter case."""
    if normalize(lang) == "ar" or not text:
        return text
    return text[:1].upper() + text[1:]


def with_article(item: str, lang: str = DEFAULT_LANG) -> str:
    """'car' -> 'a car'. Arabic does not use an indefinite article, so it passes through."""
    if not item:
        return t("item.fallback", lang)
    if normalize(lang) == "ar":
        return item
    first = item.split()[0].lower()
    if first in {"a", "an", "the", "my", "his", "her", "their", "this", "that"}:
        return item
    if item.lower().endswith("s"):  # already plural: "new tyres"
        return item
    return f"{'an' if first[0] in 'aeiou' else 'a'} {item}"


# -- Strings ----------------------------------------------------------------------------
# Keyed by string id, then language. `t()` formats with **kwargs.

STRINGS: dict[str, dict[str, str]] = {
    # --- generic ---
    "item.fallback": {"en": "the purchase", "ar": "هذا الشراء"},
    "item.subscription": {"en": "subscription", "ar": "اشتراك"},

    # --- scenario names (display only — logic uses the stable `key`) ---
    "scenario.buy_now": {"en": "Buy Now", "ar": "اشترِ الآن"},
    "scenario.wait": {"en": "Wait {months} Months", "ar": "انتظر {months} أشهر"},
    "scenario.finance": {"en": "Finance (Murabaha)", "ar": "تمويل (مرابحة)"},
    "scenario.cheaper": {"en": "Cheaper Alternative", "ar": "بديل أرخص"},
    "scenario.subscribe_now": {"en": "Subscribe Now", "ar": "اشترك الآن"},
    "scenario.pay_annually": {"en": "Pay Annually", "ar": "اشتراك سنوي"},
    "scenario.cheaper_tier": {"en": "Cheaper Tier", "ar": "باقة أرخص"},
    "scenario.skip": {"en": "Skip It", "ar": "تجاهل الاشتراك"},
    "scenario.absorb": {"en": "Absorb It", "ar": "تحمّل الأثر"},
    "scenario.trim": {"en": "Trim Spending 15%", "ar": "خفّض الإنفاق 15%"},
    "scenario.clear_loan": {"en": "Clear the Loan", "ar": "سدّد القرض"},

    # --- scenario details ---
    "detail.buy_now": {
        "en": "Pay {price} in cash today.",
        "ar": "ادفع {price} نقدًا اليوم.",
    },
    "detail.wait": {
        "en": "Save {surplus}/month for {months} months (+{added}), then pay cash.",
        "ar": "ادّخر {surplus} شهريًا لمدة {months} أشهر (+{added})، ثم ادفع نقدًا.",
    },
    "detail.finance": {
        "en": "{monthly}/month for {term} months. Total {total} — a {profit} profit "
              "markup. A conventional loan at {apr}% APR would total {conv_total}.",
        "ar": "{monthly} شهريًا لمدة {term} شهرًا. الإجمالي {total} — بهامش ربح {profit}. "
              "القرض التقليدي بفائدة سنوية {apr}% سيبلغ إجماليه {conv_total}.",
    },
    "detail.cheaper": {
        "en": "A {price} option instead ({ratio}% of the price) — saves {saved}.",
        "ar": "خيار بـ{price} بدلًا من ذلك ({ratio}% من السعر) — يوفّر {saved}.",
    },
    "detail.subscribe_now": {
        "en": "{monthly}/month — {annual} a year, and {pct}% of your monthly surplus.",
        "ar": "{monthly} شهريًا — {annual} سنويًا، أي {pct}% من فائضك الشهري.",
    },
    "detail.pay_annually": {
        "en": "{prepay} up front instead of {annual} monthly — the usual two-months-free "
              "discount saves {saved} a year.",
        "ar": "{prepay} مقدمًا بدلًا من {annual} شهريًا — خصم الشهرين المجانيين المعتاد "
              "يوفّر {saved} سنويًا.",
    },
    "detail.cheaper_tier": {
        "en": "A {monthly}/month plan instead — {saved} a year back in your pocket.",
        "ar": "باقة بـ{monthly} شهريًا بدلًا من ذلك — {saved} سنويًا تعود إلى جيبك.",
    },
    "detail.skip": {
        "en": "Save the {monthly}/month instead: {annual} more in the bank a year from now.",
        "ar": "ادّخر الـ{monthly} شهريًا بدلًا من ذلك: {annual} إضافية في حسابك بعد سنة.",
    },
    "detail.absorb": {
        "en": "Salary becomes {salary} and nothing else changes. You lose {delta}/month "
              "of surplus.",
        "ar": "يصبح الراتب {salary} ولا يتغيّر شيء آخر. تخسر {delta} شهريًا من الفائض.",
    },
    "detail.trim": {
        "en": "Cut monthly spending to {expenses} (−{saved}/month). Your emergency-fund "
              "target falls to {target} too.",
        "ar": "خفّض الإنفاق الشهري إلى {expenses} (−{saved} شهريًا). وينخفض هدف صندوق "
              "الطوارئ إلى {target} أيضًا.",
    },
    "detail.clear_loan": {
        "en": "Settle the {payoff} outstanding from savings. That frees {monthly}/month "
              "permanently.",
        "ar": "سدّد المبلغ المتبقي {payoff} من مدخراتك. هذا يحرّر {monthly} شهريًا بشكل دائم.",
    },

    # --- one-line verdicts ---
    "rec.breaks_ef": {
        "en": "Breaks your emergency fund — leaves {savings} against a {target} floor.",
        "ar": "يكسر صندوق الطوارئ — يترك {savings} مقابل حدٍّ أدنى قدره {target}.",
    },
    "rec.high": {
        "en": "Cash flow falls to {cash}/month — too thin against a {salary} salary.",
        "ar": "التدفق النقدي ينخفض إلى {cash} شهريًا — ضئيل جدًا مقابل راتب {salary}.",
    },
    "rec.medium": {
        "en": "Workable, but the margin narrows: {cash}/month spare and {cover} months "
              "of cover.",
        "ar": "ممكن، لكن الهامش يضيق: {cash} شهريًا متاحة و{cover} أشهر تغطية.",
    },
    "rec.low": {
        "en": "Comfortable — keeps {cover} months of expenses in reserve and {cash}/month "
              "spare.",
        "ar": "مريح — يبقي {cover} أشهر من المصروفات احتياطيًا و{cash} شهريًا متاحة.",
    },

    # --- alerts ---
    "alert.cannot_pay": {
        "en": "You cannot pay for {subject} in cash. It costs {cost} and you hold {savings}.",
        "ar": "لا يمكنك دفع تكلفة {subject} نقدًا. التكلفة {cost} بينما لديك {savings}.",
    },
    "alert.breaks_ef": {
        "en": "{subject} would leave you with {savings} — below your {target} emergency "
              "fund ({ef_months} months of expenses).{breach} That is {cover} months of "
              "cover instead of {ef_months}.",
        "ar": "{subject} سيترك لديك {savings} — أقل من صندوق الطوارئ البالغ {target} "
              "({ef_months} أشهر من المصروفات).{breach} أي {cover} أشهر تغطية بدلًا من "
              "{ef_months}.",
    },
    "alert.breach_suffix": {
        "en": " Your savings drop below the line in {month}.",
        "ar": " تنخفض مدخراتك تحت الحد في {month}.",
    },
    "alert.thin_cash": {
        "en": "{subject} would cut your monthly cash flow to {cash} — under 10% of your "
              "salary. One unexpected bill and you would be borrowing.",
        "ar": "{subject} سيقلّص تدفقك النقدي الشهري إلى {cash} — أقل من 10% من راتبك. "
              "فاتورة واحدة غير متوقعة وستضطر للاقتراض.",
    },
    "alert.medium": {
        "en": "{subject} is affordable but tightens things: {savings} left and {cash}/month "
              "spare. Your emergency fund survives, with {cover} months of cover.",
        "ar": "{subject} ممكن لكنه يضيّق الأمور: يتبقى {savings} و{cash} شهريًا متاحة. "
              "صندوق الطوارئ ينجو، بتغطية {cover} أشهر.",
    },
    "alert.risky_route": {
        "en": "Paying cash is safe, but the “{name}” route is not: it leaves {cash}/month "
              "spare. Compare the cards before you sign anything.",
        "ar": "الدفع نقدًا آمن، لكن مسار «{name}» ليس كذلك: يترك {cash} شهريًا فقط. قارن "
              "البطاقات قبل أن توقّع أي شيء.",
    },
    "alert.ok": {
        "en": "{subject} keeps you above your {target} emergency fund, with {cover} months "
              "of cover and {cash}/month spare.",
        "ar": "{subject} يبقيك فوق صندوق الطوارئ البالغ {target}، بتغطية {cover} أشهر "
              "و{cash} شهريًا متاحة.",
    },

    # --- timeline events ---
    "event.bought": {"en": "Bought {item} — {amount}", "ar": "شراء {item} — {amount}"},
    "event.bought_cheaper": {
        "en": "Bought a cheaper {item} — {amount}",
        "ar": "شراء {item} أرخص — {amount}",
    },
    "event.annual_plan": {
        "en": "Annual plan for {item} — {amount}",
        "ar": "اشتراك سنوي في {item} — {amount}",
    },
    "event.subscribed": {
        "en": "Subscribed to {item} — {amount}/month",
        "ar": "الاشتراك في {item} — {amount} شهريًا",
    },
    "event.financed": {
        "en": "Financed {item} — {amount}/month for {term} months",
        "ar": "تمويل {item} — {amount} شهريًا لمدة {term} شهرًا",
    },
    "event.loan_cleared": {
        "en": "{name} cleared — {amount}/month freed up",
        "ar": "تم سداد {name} — تحرير {amount} شهريًا",
    },
    "event.financing_done": {
        "en": "Financing complete — {amount}/month freed up",
        "ar": "انتهى التمويل — تحرير {amount} شهريًا",
    },
    "event.loan_settled": {
        "en": "Loan settled — {amount} paid, {monthly}/month freed",
        "ar": "تم سداد القرض — دُفع {amount}، وتحرّر {monthly} شهريًا",
    },
    "event.salary_change": {
        "en": "Salary changes to {amount}/month",
        "ar": "يتغيّر الراتب إلى {amount} شهريًا",
    },
    "event.liability": {
        "en": "{name}: {amount}/month, {months} months remaining",
        "ar": "{name}: {amount} شهريًا، متبقٍ {months} شهرًا",
    },

    # --- timeline warnings ---
    "warn.below_ef": {
        "en": "Savings drop below your {target} emergency fund",
        "ar": "المدخرات تنخفض تحت صندوق الطوارئ البالغ {target}",
    },
    "warn.still_below": {
        "en": "Still below your emergency fund",
        "ar": "لا تزال تحت صندوق الطوارئ",
    },
    "warn.exhausted": {
        "en": "Savings exhausted — you would need to borrow",
        "ar": "نفدت المدخرات — ستضطر للاقتراض",
    },

    # --- subjects (what is being simulated) ---
    "subject.purchase": {
        "en": "buying {item} for {price}",
        "ar": "شراء {item} بمبلغ {price}",
    },
    "subject.recurring": {
        "en": "a {price}/month {item}",
        "ar": "{item} بقيمة {price} شهريًا",
    },
    "subject.income": {
        "en": "a {pct}% salary {direction}",
        "ar": "{direction} الراتب بنسبة {pct}%",
    },
    "direction.drop": {"en": "drop", "ar": "انخفاض"},
    "direction.rise": {"en": "rise", "ar": "ارتفاع"},

    # --- health score ---
    "health.excellent": {"en": "Excellent", "ar": "ممتاز"},
    "health.good": {"en": "Good", "ar": "جيد"},
    "health.fair": {"en": "Fair", "ar": "مقبول"},
    "health.at_risk": {"en": "At risk", "ar": "في خطر"},
    "health.critical": {"en": "Critical", "ar": "حرج"},
    "health.savings_rate": {"en": "Savings rate", "ar": "معدل الادخار"},
    "health.emergency_fund": {"en": "Emergency fund", "ar": "صندوق الطوارئ"},
    "health.debt_to_income": {"en": "Debt-to-income", "ar": "نسبة الدين إلى الدخل"},
    "health.goal_progress": {"en": "Goal progress", "ar": "التقدم نحو الهدف"},
    "unit.months": {"en": " months", "ar": " أشهر"},

    # --- template answers (used when the LLM is unavailable) ---
    "tpl.careful": {"en": "**Careful.**", "ar": "**انتبه.**"},
    "tpl.proceed": {"en": "**Proceed carefully.**", "ar": "**تقدّم بحذر.**"},
    "tpl.works": {"en": "**Yes — this works.**", "ar": "**نعم — هذا ممكن.**"},
    "tpl.recommend": {
        "en": "My recommendation is **{name}**: {detail} That leaves you **{savings}** in "
              "savings and **{cash}/month** of breathing room — {cover} months of expenses "
              "covered, against your {target} emergency-fund target. Risk: **{risk}**.",
        "ar": "توصيتي هي **{name}**: {detail} هذا يترك لديك **{savings}** مدخرات "
              "و**{cash} شهريًا** من الأريحية — تغطية {cover} أشهر من المصروفات، مقابل هدف "
              "صندوق الطوارئ البالغ {target}. المخاطرة: **{risk}**.",
    },
    "tpl.worth_knowing": {
        "en": "Worth knowing: **{name}** is the {risk}-risk route — {recommendation}",
        "ar": "جدير بالمعرفة: **{name}** هو المسار ذو المخاطرة {risk} — {recommendation}",
    },
    "tpl.goal_delay": {
        "en": "This pushes your goals back by about **{months} months**.",
        "ar": "هذا يؤخّر أهدافك بنحو **{months} أشهر**.",
    },
    "tpl.source": {"en": "(source: {source})", "ar": "(المصدر: {source})"},
    "tpl.kb_intro": {
        "en": "Here’s what my knowledge base says, grounded in your numbers "
              "(**{savings}** saved, **{surplus}/month** spare):",
        "ar": "إليك ما تقوله قاعدة معرفتي، مستندًا إلى أرقامك (**{savings}** مدخرات، "
              "و**{surplus} شهريًا** متاحة):",
    },
    "tpl.no_llm": {
        "en": "I can’t reach my language model right now, but your Twin is still here. You "
              "have **{savings}** saved, **{surplus}/month** spare, and an emergency-fund "
              "target of **{target}**. Ask me about a specific purchase — for example "
              "*“what if I buy a car for 120,000 SAR?”* — and I can simulate it exactly.",
        "ar": "لا أستطيع الوصول إلى نموذجي اللغوي حاليًا، لكن توأمك المالي لا يزال هنا. "
              "لديك **{savings}** مدخرات، و**{surplus} شهريًا** متاحة، وهدف صندوق طوارئ "
              "قدره **{target}**. اسألني عن عملية شراء محددة — مثلًا *«ماذا لو اشتريت "
              "سيارة بـ120,000 ريال؟»* — وسأحاكيها بدقة.",
    },
    "tpl.chitchat": {
        "en": "Hello {name} — I’m your Financial Twin. Ask me about a purchase before you "
              "make it and I’ll show you exactly what it does to your savings, your cash "
              "flow, and your goals. Try *“what if I buy a car for 120,000 SAR?”*",
        "ar": "أهلًا {name} — أنا توأمك المالي. اسألني عن أي عملية شراء قبل أن تقوم بها "
              "وسأريك بالضبط أثرها على مدخراتك وتدفقك النقدي وأهدافك. جرّب *«ماذا لو "
              "اشتريت سيارة بـ120,000 ريال؟»*",
    },

    # --- risk words, for the template writer ---
    "risk.low": {"en": "low", "ar": "منخفضة"},
    "risk.medium": {"en": "medium", "ar": "متوسطة"},
    "risk.high": {"en": "high", "ar": "مرتفعة"},

    # --- API error messages ---
    "err.empty": {
        "en": "Say something and I’ll run the numbers.",
        "ar": "اكتب شيئًا وسأحسب الأرقام.",
    },
    "err.too_long": {
        "en": "That message is too long — try asking in a sentence or two.",
        "ar": "الرسالة طويلة جدًا — حاول السؤال في جملة أو جملتين.",
    },
    "err.generic": {
        "en": "Something went wrong on my side. Your data is safe — try asking again.",
        "ar": "حدث خطأ من جانبي. بياناتك بأمان — حاول السؤال مرة أخرى.",
    },
    "err.chat": {
        "en": "I couldn’t finish that one. My simulation engine is fine — it’s my language "
              "model that stumbled. Try rephrasing, or ask about a specific purchase.",
        "ar": "لم أتمكن من إكمال ذلك. محرك المحاكاة يعمل جيدًا — النموذج اللغوي هو من تعثّر. "
              "حاول إعادة الصياغة، أو اسأل عن عملية شراء محددة.",
    },
    "err.profile": {
        "en": "Couldn’t load your Financial Twin.",
        "ar": "تعذّر تحميل توأمك المالي.",
    },
    "err.timeline": {
        "en": "Couldn’t build your projection.",
        "ar": "تعذّر بناء التوقعات.",
    },
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: Any) -> str:
    """Look up a string and format it. Falls back to English, then to the key itself, so a
    missing translation degrades into something readable rather than a KeyError."""
    lang = normalize(lang)
    entry = STRINGS.get(key)
    if not entry:
        return key
    template = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template
