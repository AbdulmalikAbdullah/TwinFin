/**
 * UI copy, in both languages.
 *
 * Only *chrome* lives here — labels, headings, buttons. Everything the Twin actually says
 * (scenario names, verdicts, alerts, timeline events) is localised by the Python engine
 * and arrives already translated, because that text is generated from the numbers and has
 * to stay in lockstep with them.
 *
 * `tr()` is deliberately usable outside React, so api.js can translate its own errors.
 */

export const LANGS = ['en', 'ar']
export const RTL_LANGS = ['ar']

export const isRtl = (lang) => RTL_LANGS.includes(lang)

export const STRINGS = {
  en: {
    // -- nav ---------------------------------------------------------------------------
    'nav.home': 'Home',
    'nav.dashboard': 'Dashboard',
    'nav.chat': 'Chat',
    'nav.switchLang': 'العربية',
    'nav.switchLangAria': 'Switch to Arabic',

    // -- landing -----------------------------------------------------------------------
    'landing.badge': 'New',
    'landing.eyebrow': 'Your AI Financial Twin — built for Saudi Arabia',
    'landing.title1': 'Ask your Twin',
    'landing.titleEm': 'before',
    'landing.title2': 'you spend.',
    'landing.sub':
      'Twin simulates what a purchase actually does to your future — your savings, your monthly breathing room, your emergency fund, and how far it pushes back the goals you already said mattered. Before you buy, not after.',
    'landing.ctaPrimary': 'Ask your Twin',
    'landing.ctaSecondary': 'See the dashboard',
    'landing.note': 'Try it:',
    'landing.noteExample': '“What if I buy a car for 220,000 SAR?”',

    'landing.f1.title': 'The maths is not guessed',
    'landing.f1.body':
      'Every figure — savings left, cash flow, goal delay, health score — is computed by a deterministic Python engine. The language model explains the numbers. It never invents them.',
    'landing.f2.title': 'Four futures, side by side',
    'landing.f2.body':
      'Buy now, wait six months, finance it with murabaha, or buy cheaper. Twin costs all four against your real profile and ranks them by risk — never by what you want to hear.',
    'landing.f3.title': 'It warns you before you sign',
    'landing.f3.body':
      'If a purchase would take you below six months of expenses or leave your cash flow too thin, Twin says so — loudly — and shows you what to do instead.',

    // -- dashboard ---------------------------------------------------------------------
    'dash.title': '{name}’s Financial Twin',
    'dash.titleFallback': 'Your Financial Twin',
    'dash.sub': '{age} · {city} · risk tolerance: {risk}',
    'dash.loading': 'Loading your profile…',
    'dash.cta': 'Simulate a purchase',

    'dash.salary': 'Salary',
    'dash.salaryMeta': '{surplus} spare after expenses and debt',
    'dash.savings': 'Savings',
    'dash.savingsMeta': '{months} months of expenses covered',
    'dash.expenses': 'Monthly expenses',
    'dash.expensesMeta': '+ {debt} of debt service',
    'dash.health': 'Financial health',

    'dash.projTitle': 'Next 12 months, if nothing changes',
    'dash.projSub':
      'Saving {surplus} a month. The dashed red line is your emergency-fund floor.',
    'dash.projLoading': 'Building your projection…',

    'dash.goals': 'Goals',
    'dash.goalsSub': 'Progress counts only savings above your buffer',
    'dash.goalHorizon': 'within {months} months',
    'dash.liabilities': 'Liabilities',
    'dash.liabilityMeta': '{amount}/mo · {months} mo left',
    'dash.spending': 'Where it goes',
    'dash.spendingSub': 'Monthly',

    'dash.standingOk':
      'Your emergency fund is intact — {months} months of expenses in cash, against a {target} target. You have {surplus} spare every month.',
    'dash.standingBad':
      'Your savings are below your {target} emergency fund. Rebuild it before anything else.',

    // -- chat --------------------------------------------------------------------------
    'chat.emptyTitle': 'Ask before you spend.',
    'chat.emptySub':
      'Tell me what you’re thinking of buying and I’ll show you exactly what it does to your savings, your monthly breathing room, and your goals — with the real numbers, not a vibe.',
    'chat.placeholder': 'What are you thinking of buying?',
    'chat.you': 'You',
    'chat.twin': 'Twin',
    'chat.thinking': 'Twin is thinking',
    'chat.groundedIn': 'Grounded in',
    'chat.send': 'Send',

    'chat.chip1': 'What if I buy a car for 120,000 SAR?',
    'chat.chip2': 'What if I buy a car for 220,000 SAR?',
    'chat.chip3': 'Can I afford a 300 SAR/month subscription?',
    'chat.chip4': 'What if I wait six months?',
    'chat.chip5': 'What happens if my salary drops 20%?',

    // -- scenario card -----------------------------------------------------------------
    'scn.recommended': 'Recommended',
    'scn.savingsLeft': 'Savings left',
    'scn.cashFlow': 'Cash flow',
    'scn.emergencyFund': 'Emergency fund',
    'scn.installment': 'Installment',
    'scn.goalDelay': 'Goal delay',
    'scn.healthScore': 'Health score',
    'scn.none': 'None',
    'scn.mo': 'mo',
    'scn.perMonth': '/mo',

    'risk.low': 'Low risk',
    'risk.medium': 'Medium risk',
    'risk.high': 'High risk',

    // -- chart -------------------------------------------------------------------------
    'chart.savings': 'Savings',
    'chart.income': 'Income',
    'chart.outgoings': 'Outgoings',
    'chart.purchase': 'Purchase',
    'chart.floor': 'Emergency fund',
    'chart.projection': '{name} — 12-month projection',
    'chart.compare': 'Tap another card to compare.',
    'chart.endsAt': 'Ends at',
    'chart.totalCost': 'total cost',

    // -- alerts ------------------------------------------------------------------------
    'alert.danger': 'Twin is warning you',
    'alert.warning': 'Proceed carefully',
    'alert.info': 'You’re in the clear',

    // -- errors ------------------------------------------------------------------------
    'err.unreachable':
      'I can’t reach the Twin backend. Start it with `python backend/app.py` and try again.',
    'err.timeout': 'That took too long. Try asking again — the model may be busy.',
    'err.unreadable':
      'I couldn’t read the server’s reply. Is the backend running on port 5000?',
    'err.status': 'The server returned {status}.',
  },

  ar: {
    // -- nav ---------------------------------------------------------------------------
    'nav.home': 'الرئيسية',
    'nav.dashboard': 'لوحة التحكم',
    'nav.chat': 'المحادثة',
    'nav.switchLang': 'English',
    'nav.switchLangAria': 'التبديل إلى الإنجليزية',

    // -- landing -----------------------------------------------------------------------
    'landing.badge': 'جديد',
    'landing.eyebrow': 'توأمك المالي بالذكاء الاصطناعي — مصمّم للسعودية',
    'landing.title1': 'اسأل توأمك',
    'landing.titleEm': 'قبل',
    'landing.title2': 'أن تنفق.',
    'landing.sub':
      'يحاكي «توأم» ما تفعله عملية الشراء فعلًا بمستقبلك — مدخراتك، وأريحيتك الشهرية، وصندوق طوارئك، وكم ستؤخّر الأهداف التي قلت إنها تهمّك. قبل أن تشتري، لا بعد ذلك.',
    'landing.ctaPrimary': 'اسأل توأمك',
    'landing.ctaSecondary': 'شاهد لوحة التحكم',
    'landing.note': 'جرّب:',
    'landing.noteExample': '«ماذا لو اشتريت سيارة بـ 220,000 ريال؟»',

    'landing.f1.title': 'الأرقام ليست تخمينًا',
    'landing.f1.body':
      'كل رقم — المدخرات المتبقية، والتدفق النقدي، وتأخير الهدف، ودرجة الصحة المالية — يحسبه محرك بايثون حتمي. النموذج اللغوي يشرح الأرقام فقط، ولا يخترعها أبدًا.',
    'landing.f2.title': 'أربعة مستقبلات جنبًا إلى جنب',
    'landing.f2.body':
      'اشترِ الآن، أو انتظر ستة أشهر، أو موّلها بالمرابحة، أو اشترِ أرخص. يحسب «توأم» الأربعة على ملفك الحقيقي ويرتّبها حسب المخاطرة — لا حسب ما تحب أن تسمعه.',
    'landing.f3.title': 'ينبّهك قبل أن توقّع',
    'landing.f3.body':
      'إذا كانت عملية الشراء ستنزل بك تحت ستة أشهر من المصروفات أو تترك تدفقك النقدي ضعيفًا، سيقولها «توأم» بوضوح — ويريك ما تفعله بدلًا من ذلك.',

    // -- dashboard ---------------------------------------------------------------------
    'dash.title': 'التوأم المالي لـ{name}',
    'dash.titleFallback': 'توأمك المالي',
    'dash.sub': '{age} · {city} · تحمّل المخاطر: {risk}',
    'dash.loading': 'جارٍ تحميل ملفك…',
    'dash.cta': 'حاكِ عملية شراء',

    'dash.salary': 'الراتب',
    'dash.salaryMeta': '{surplus} متاحة بعد المصروفات والديون',
    'dash.savings': 'المدخرات',
    'dash.savingsMeta': 'تغطية {months} أشهر من المصروفات',
    'dash.expenses': 'المصروفات الشهرية',
    'dash.expensesMeta': '+ {debt} خدمة دين',
    'dash.health': 'الصحة المالية',

    'dash.projTitle': 'الأشهر الاثنا عشر القادمة، إن لم يتغيّر شيء',
    'dash.projSub': 'ادخار {surplus} شهريًا. الخط الأحمر المتقطع هو حد صندوق الطوارئ.',
    'dash.projLoading': 'جارٍ بناء التوقعات…',

    'dash.goals': 'الأهداف',
    'dash.goalsSub': 'التقدّم يحتسب فقط المدخرات فوق حد الأمان',
    'dash.goalHorizon': 'خلال {months} شهرًا',
    'dash.liabilities': 'الالتزامات',
    'dash.liabilityMeta': '{amount} شهريًا · متبقٍ {months} شهرًا',
    'dash.spending': 'أين تذهب أموالك',
    'dash.spendingSub': 'شهريًا',

    'dash.standingOk':
      'صندوق طوارئك سليم — {months} أشهر من المصروفات نقدًا، مقابل هدف {target}. ولديك {surplus} متاحة كل شهر.',
    'dash.standingBad':
      'مدخراتك أقل من صندوق الطوارئ البالغ {target}. أعد بناءه قبل أي شيء آخر.',

    // -- chat --------------------------------------------------------------------------
    'chat.emptyTitle': 'اسأل قبل أن تنفق.',
    'chat.emptySub':
      'أخبرني بما تفكّر في شرائه وسأريك بالضبط أثره على مدخراتك، وأريحيتك الشهرية، وأهدافك — بالأرقام الحقيقية، لا بالانطباعات.',
    'chat.placeholder': 'ما الذي تفكّر في شرائه؟',
    'chat.you': 'أنت',
    'chat.twin': 'توأم',
    'chat.thinking': 'توأم يفكّر',
    'chat.groundedIn': 'مستند إلى',
    'chat.send': 'إرسال',

    'chat.chip1': 'ماذا لو اشتريت سيارة بـ 120,000 ريال؟',
    'chat.chip2': 'ماذا لو اشتريت سيارة بـ 220,000 ريال؟',
    'chat.chip3': 'هل أقدر على اشتراك بـ 300 ريال شهريًا؟',
    'chat.chip4': 'ماذا لو انتظرت ستة أشهر؟',
    'chat.chip5': 'ماذا يحدث إذا انخفض راتبي بنسبة 20%؟',

    // -- scenario card -----------------------------------------------------------------
    'scn.recommended': 'موصى به',
    'scn.savingsLeft': 'المدخرات المتبقية',
    'scn.cashFlow': 'التدفق النقدي',
    'scn.emergencyFund': 'صندوق الطوارئ',
    'scn.installment': 'القسط',
    'scn.goalDelay': 'تأخير الهدف',
    'scn.healthScore': 'الصحة المالية',
    'scn.none': 'لا يوجد',
    'scn.mo': 'شهر',
    'scn.perMonth': ' شهريًا',

    'risk.low': 'مخاطرة منخفضة',
    'risk.medium': 'مخاطرة متوسطة',
    'risk.high': 'مخاطرة مرتفعة',

    // -- chart -------------------------------------------------------------------------
    'chart.savings': 'المدخرات',
    'chart.income': 'الدخل',
    'chart.outgoings': 'المصروفات',
    'chart.purchase': 'الشراء',
    'chart.floor': 'صندوق الطوارئ',
    'chart.projection': '{name} — توقعات 12 شهرًا',
    'chart.compare': 'اضغط بطاقة أخرى للمقارنة.',
    'chart.endsAt': 'ينتهي عند',
    'chart.totalCost': 'التكلفة الإجمالية',

    // -- alerts ------------------------------------------------------------------------
    'alert.danger': 'توأمك ينبّهك',
    'alert.warning': 'تقدّم بحذر',
    'alert.info': 'أنت في وضع آمن',

    // -- errors ------------------------------------------------------------------------
    'err.unreachable':
      'لا أستطيع الوصول إلى خادم «توأم». شغّله بالأمر `python backend/app.py` ثم حاول مجددًا.',
    'err.timeout': 'استغرق ذلك وقتًا طويلًا. حاول مرة أخرى — قد يكون النموذج مشغولًا.',
    'err.unreadable': 'تعذّرت قراءة رد الخادم. هل الخادم يعمل على المنفذ 5000؟',
    'err.status': 'أعاد الخادم الرمز {status}.',
  },
}

/** Translate outside of React. Falls back to English, then to the key itself. */
export function tr(lang, key, vars) {
  const table = STRINGS[lang] ?? STRINGS.en
  let text = table[key] ?? STRINGS.en[key] ?? key
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${name}}`, String(value))
    }
  }
  return text
}
