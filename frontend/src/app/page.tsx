"use client";

import { useEffect, useMemo, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const profile = {
  monthlySalary: 18000,
  savings: 250000,
  monthlyExpenses: 9000,
  goal: 'شراء بيت',
  financialHealthScore: 82,
  assets: 420000,
  liabilities: 115000,
  emergencyFund: 120000,
};

const englishScenarioCards = [
  { name: 'Buy Now', impact: -120000, risk: 'High', recommendation: 'Delay if the purchase affects your emergency fund.' },
  { name: 'Wait 6 Months', impact: -60000, risk: 'Medium', recommendation: 'Build momentum and protect cash flow.' },
  { name: 'Finance', impact: -90000, risk: 'High', recommendation: 'Only if the monthly payment stays below 20% of income.' },
  { name: 'Cheaper Alternative', impact: -45000, risk: 'Low', recommendation: 'A strong option that preserves savings.' },
];

const arabicScenarioCards = [
  { name: 'شراء الآن', impact: -120000, risk: 'مرتفع', recommendation: 'أجل الشراء إذا كان سيؤثر على صندوق الطوارئ.' },
  { name: 'انتظار 6 أشهر', impact: -60000, risk: 'متوسط', recommendation: 'امنح نفسك وقتًا لبناء التوازن المالي.' },
  { name: 'التمويل', impact: -90000, risk: 'مرتفع', recommendation: 'فقط إذا بقيت الدفعة الشهرية أقل من 20% من الدخل.' },
  { name: 'بديل أرخص', impact: -45000, risk: 'منخفض', recommendation: 'خيار قوي يحافظ على السيولة.' },
];

const timelineData = Array.from({ length: 12 }, (_, index) => ({
  month: `ش${index + 1}`,
  balance: profile.savings - index * 8000 + (index % 3 === 0 ? 0 : 3000),
  income: profile.monthlySalary,
  expenses: profile.monthlyExpenses + (index % 2 === 0 ? 500 : 0),
}));

function renderMessageContent(content: string) {
  const normalized = content.replace(/\r/g, '').trim();
  if (!normalized) return null;

  const lines = normalized.split('\n').map((line) => line.trim()).filter(Boolean);
  const bulletLines = lines.filter((line) => /^\s*(?:[-*•]|\d+\.)\s+/.test(line));
  const otherLines = lines.filter((line) => !/^\s*(?:[-*•]|\d+\.)\s+/.test(line));

  if (bulletLines.length > 0) {
    return (
      <div className="space-y-2">
        {otherLines.map((line, index) => {
          const match = line.match(/^([A-Za-zأ-ي\s]+):\s*(.+)$/);
          if (match) {
            return (
              <div key={`${line}-${index}`} className="rounded-2xl bg-orange-50/80 px-3 py-2 text-sm text-dark">
                <span className="font-semibold">{match[1]}:</span> {match[2]}
              </div>
            );
          }
          return <p key={`${line}-${index}`} className="text-sm leading-7 text-dark">{line}</p>;
        })}
        <ul className="list-disc space-y-1 pr-5 text-sm leading-7 text-darkSecondary">
          {bulletLines.map((line, index) => (
            <li key={`${line}-${index}`}>{line.replace(/^\s*(?:[-*•]|\d+\.)\s+/, '')}</li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {lines.map((line, index) => {
        const match = line.match(/^([A-Za-zأ-ي\s]+):\s*(.+)$/);
        if (match) {
          return (
            <div key={`${line}-${index}`} className="rounded-2xl bg-orange-50/80 px-3 py-2 text-sm text-dark">
              <span className="font-semibold">{match[1]}:</span> {match[2]}
            </div>
          );
        }
        return <p key={`${line}-${index}`} className="text-sm leading-7 text-dark">{line}</p>;
      })}
    </div>
  );
}

export default function HomePage() {
  const [language, setLanguage] = useState<'ar' | 'en'>('ar');
  const isArabic = language === 'ar';
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([
    { role: 'assistant', content: 'مرحبًا، أنا التوأم. أستطيع مساعدتك في تقييم أي قرار شراء قبل أن تنفق.' },
  ]);
  const [input, setInput] = useState('');
  const [insights, setInsights] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const initialInsights = isArabic
      ? [
          'صندوق الطوارئ لديك قوي بما يكفي لوقف مؤقت قصير.',
          'تأجيل الشراء ستة أشهر قد يُحسّن المسار المالي لك بحوالي 3 أشهر.',
          'الطريق الأكثر توازنًا هو اختيار بديل أرخص مع الحفاظ على السيولة.',
        ]
      : [
          'Your emergency fund is strong enough for a short-term pause.',
          'A six-month delay would improve your goal timeline by roughly 3 months.',
          'The most balanced path is a cheaper alternative with preserved liquidity.',
        ];
    setInsights(initialInsights);
    setMessages([
      {
        role: 'assistant',
        content: isArabic
          ? 'مرحبًا، أنا التوأم. أستطيع مساعدتك في تقييم أي قرار شراء قبل أن تنفق.'
          : 'Hi, I’m Tawam. I can help you assess a purchase before you spend.',
      },
    ]);
  }, [isArabic]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!input.trim()) return;
    const question = input.trim();
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:8002/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });
      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer }]);
      setInsights(data.insights);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: isArabic
            ? 'الخادم غير متاح حاليًا، لكن لوحة التحكم ما زالت توضح تجربة التوأم بشكل واضح.'
            : 'The backend is currently unavailable, but the dashboard still demonstrates the Tawam experience clearly.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const summary = useMemo(() => {
    const remaining = profile.savings - 120000;
    const monthlyFlow = profile.monthlySalary - profile.monthlyExpenses;
    return {
      remainingSavings: remaining,
      monthlyCashFlow: monthlyFlow,
      recommendation: remaining > 150000 ? (isArabic ? 'تابع بحذر' : 'Proceed with caution') : (isArabic ? 'أوقف وانظر مرة أخرى' : 'Pause and review'),
    };
  }, [isArabic]);

  const scenarioCards = isArabic ? arabicScenarioCards : englishScenarioCards;
  const copy = {
    title: isArabic ? 'التوأم' : 'Tawam',
    subtitle: isArabic
      ? 'جرّب السيناريوهات قبل الإنفاق، وتعرّف على أثر كل قرار على ميزانيتك وعلى هدفك المالي.'
      : 'Test scenarios before spending and understand the impact of each decision on your cash flow and goal.',
    scoreLabel: isArabic ? 'درجة الصحة المالية' : 'Financial Health Score',
    twinTitle: isArabic ? 'ملخصك الشهري' : 'Your monthly snapshot',
    twinSubtitle: isArabic ? 'لوحة واضحة وسريعة' : 'A clear snapshot of your finances',
    scenarioTitle: isArabic ? 'نتيجة التوقعات' : 'Projected outcome',
    remainingLabel: isArabic ? 'الرصيد المتبقي' : 'Remaining Savings',
    cashFlowLabel: isArabic ? 'التدفق الشهري' : 'Monthly Cash Flow',
    recommendationLabel: isArabic ? 'التوصية' : 'Recommendation',
    chatTitle: isArabic ? 'اسأل التوأم عن أي شراء' : 'Ask Tawam about a purchase',
    chatSubtitle: isArabic ? 'اكتب سؤالك بطريقة بسيطة' : 'Ask in a simple way',
    inputPlaceholder: isArabic ? 'ماذا لو اشتريت سيارة بقيمة 120,000 ريال؟' : 'What if I buy a car for 120,000 SAR?',
    buttonLabel: isArabic ? 'اسأل التوأم' : 'Ask Tawam',
    insightsTitle: isArabic ? 'رؤى مالية مهمة' : 'Financial insights',
    comparisonTitle: isArabic ? 'مقارنة السيناريوهات' : 'Scenario comparison',
    timelineTitle: isArabic ? 'المسار خلال 12 شهرًا' : '12-Month timeline',
    riskLabel: isArabic ? 'المخاطرة' : 'Risk',
    impactLabel: isArabic ? 'الأثر' : 'Impact',
    monthLabel: isArabic ? 'شهر' : 'Month',
    toggleLabel: isArabic ? 'English' : 'العربية',
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(216,101,59,0.16),_transparent_35%),radial-gradient(circle_at_top_right,_rgba(134,133,216,0.14),_transparent_35%)] px-4 py-8 text-dark sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-8">
        <header className="rounded-[32px] border border-white/70 bg-white/70 px-6 py-6 shadow-soft backdrop-blur-xl">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="text-right">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-primary">التوأم</p>
                <button
                  type="button"
                  onClick={() => setLanguage(isArabic ? 'en' : 'ar')}
                  className="rounded-full border border-surface bg-surface px-3 py-1 text-sm font-semibold text-dark"
                >
                  {copy.toggleLabel}
                </button>
              </div>
              <h1 className="mt-2 text-4xl font-semibold text-dark">{copy.title}</h1>
              <p className="mt-3 max-w-2xl text-lg text-darkSecondary">{copy.subtitle}</p>
            </div>
            <div className="rounded-2xl bg-dark px-5 py-4 text-white">
              <div className="text-sm text-white/70">{copy.scoreLabel}</div>
              <div className="mt-1 text-3xl font-semibold">{profile.financialHealthScore}/100</div>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[32px] border border-surface bg-white/80 p-6 shadow-soft backdrop-blur-xl">
            <div className="flex items-center justify-between gap-3">
              <div className="text-right">
                <p className="text-sm font-semibold uppercase tracking-[0.25em] text-secondary">{copy.twinSubtitle}</p>
                <h2 className="mt-2 text-2xl font-semibold text-dark">{copy.twinTitle}</h2>
              </div>
              <div className="rounded-full bg-surface px-3 py-1 text-sm font-medium text-dark">MVP</div>
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {[
                [isArabic ? 'الدخل الشهري' : 'Monthly Salary', `SAR ${profile.monthlySalary.toLocaleString()}`],
                [isArabic ? 'المدخرات' : 'Savings', `SAR ${profile.savings.toLocaleString()}`],
                [isArabic ? 'المصروفات الشهرية' : 'Monthly Expenses', `SAR ${profile.monthlyExpenses.toLocaleString()}`],
                [isArabic ? 'الهدف المالي' : 'Financial Goal', profile.goal],
              ].map(([label, value]) => (
                <div key={label as string} className="rounded-2xl border border-surface bg-surface/50 p-4 text-right">
                  <div className="text-sm text-darkSecondary">{label}</div>
                  <div className="mt-2 text-xl font-semibold text-dark">{value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[32px] border border-surface bg-dark p-6 text-white shadow-soft">
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-secondary">{copy.scenarioTitle}</p>
            <h2 className="mt-2 text-2xl font-semibold">{copy.scenarioTitle}</h2>
            <div className="mt-6 grid gap-4 text-right">
              <div className="rounded-2xl bg-white/10 p-4">
                <div className="text-sm text-white/70">{copy.remainingLabel}</div>
                <div className="mt-1 text-2xl font-semibold">SAR {summary.remainingSavings.toLocaleString()}</div>
              </div>
              <div className="rounded-2xl bg-white/10 p-4">
                <div className="text-sm text-white/70">{copy.cashFlowLabel}</div>
                <div className="mt-1 text-2xl font-semibold">SAR {summary.monthlyCashFlow.toLocaleString()}</div>
              </div>
              <div className="rounded-2xl bg-white/10 p-4">
                <div className="text-sm text-white/70">{copy.recommendationLabel}</div>
                <div className="mt-1 text-lg font-semibold">{summary.recommendation}</div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[32px] border border-surface bg-white/80 p-6 shadow-soft backdrop-blur-xl">
            <div className="flex items-center justify-between gap-3">
              <div className="text-right">
                <p className="text-sm font-semibold uppercase tracking-[0.25em] text-primary">AI</p>
                <h2 className="mt-2 text-2xl font-semibold text-dark">{copy.chatTitle}</h2>
                <p className="mt-1 text-sm text-darkSecondary">{copy.chatSubtitle}</p>
              </div>
            </div>
            <div className="mt-6 space-y-3 rounded-3xl bg-surface/50 p-4 text-right">
              {messages.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`rounded-2xl px-4 py-3 ${message.role === 'user' ? 'ml-8 bg-dark text-white' : 'mr-8 bg-white text-dark'}`}>
                  {message.role === 'assistant' ? renderMessageContent(message.content) : <p className="text-sm leading-7">{message.content}</p>}
                </div>
              ))}
              {isLoading && <div className="mr-8 rounded-2xl bg-white px-4 py-3 text-dark">{isArabic ? 'أحلل السيناريو الآن…' : 'Analyzing your scenario…'}</div>}
            </div>
            <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder={copy.inputPlaceholder}
                className="flex-1 rounded-2xl border border-surface bg-white px-4 py-3 text-right outline-none ring-0"
              />
              <button className="rounded-2xl bg-primary px-5 py-3 font-semibold text-white">{copy.buttonLabel}</button>
            </form>
          </div>

          <div className="rounded-[32px] border border-surface bg-white/80 p-6 shadow-soft backdrop-blur-xl text-right">
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-secondary">{copy.insightsTitle}</p>
            <ul className="mt-4 space-y-3">
              {insights.map((insight) => (
                <li key={insight} className="rounded-2xl border border-surface bg-surface/60 p-3 text-sm text-darkSecondary">{insight}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
          <div className="rounded-[32px] border border-surface bg-white/80 p-6 shadow-soft backdrop-blur-xl text-right">
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-primary">{copy.comparisonTitle}</p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              {scenarioCards.map((card) => (
                <div key={card.name} className="rounded-3xl border border-surface bg-surface/50 p-4">
                  <div className="text-lg font-semibold text-dark">{card.name}</div>
                  <div className="mt-2 text-sm text-darkSecondary">{card.recommendation}</div>
                  <div className="mt-4 text-sm">{copy.impactLabel}: <span className="font-semibold">SAR {Math.abs(card.impact).toLocaleString()}</span></div>
                  <div className="mt-1 text-sm">{copy.riskLabel}: <span className="font-semibold">{card.risk}</span></div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[32px] border border-surface bg-white/80 p-6 shadow-soft backdrop-blur-xl text-right">
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-secondary">{copy.timelineTitle}</p>
            <div className="mt-5 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timelineData}>
                  <defs>
                    <linearGradient id="balance" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#D8653B" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#D8653B" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Area type="monotone" dataKey="balance" stroke="#D8653B" fillOpacity={1} fill="url(#balance)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
