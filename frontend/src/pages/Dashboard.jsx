import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import AlertBanner from '../components/AlertBanner'
import HealthGauge from '../components/HealthGauge'
import TimelineChart from '../components/TimelineChart'
import { getProfile, getTimeline } from '../lib/api'
import { useLang } from '../lib/i18n'
import { CHART, sar } from '../lib/format'

const EXPENSE_COLOURS = ['#D8653B', '#8685D8', '#212145', '#1F8A5F', '#C8393A']

function StatCard({ label, value, meta }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value num">{value}</div>
      {meta && <div className="stat-meta">{meta}</div>}
    </div>
  )
}

function StatSkeleton() {
  return (
    <div className="stat">
      <div className="skeleton" style={{ height: 11, width: 70 }} />
      <div className="skeleton" style={{ height: 27, width: 120, marginTop: 14 }} />
      <div className="skeleton" style={{ height: 12, width: 100, marginTop: 12 }} />
    </div>
  )
}

export default function Dashboard() {
  const { t, lang } = useLang()
  const [data, setData] = useState(null)
  const [timeline, setTimeline] = useState(null)
  const [error, setError] = useState(null)

  // Refetch on language change: the backend localises goal names, liability names, month
  // labels and the health-score band, so a language switch is a data change, not just a
  // re-render.
  useEffect(() => {
    let cancelled = false
    setError(null)

    Promise.all([getProfile(lang), getTimeline(lang)]).then(([p, tl]) => {
      if (cancelled) return
      // A failure in either call surfaces as a friendly banner, never a blank page.
      if (p.error || tl.error) {
        setError(p.error || tl.error)
        return
      }
      setData(p)
      setTimeline(tl)
    })

    return () => {
      cancelled = true
    }
  }, [lang])

  if (error) {
    return (
      <div className="container page">
        <div className="error-box">{error}</div>
      </div>
    )
  }

  const p = data?.profile
  const floor = p?.emergency_fund_target ?? 0
  const covered = p ? (p.savings / p.monthly_expenses).toFixed(1) : null

  // Baseline is healthy by construction, but the banner area is live: it reflects the
  // Twin's standing verdict on the profile as it is today.
  const standing = p
    ? p.savings >= floor
      ? {
          level: 'info',
          message: t('dash.standingOk', {
            months: covered,
            target: sar(floor, lang),
            surplus: sar(p.monthly_surplus, lang),
          }),
        }
      : {
          level: 'danger',
          message: t('dash.standingBad', { target: sar(floor, lang) }),
        }
    : null

  return (
    <div className="container page">
      <div className="page-head">
        <div>
          <div className="page-title">
            {p ? t('dash.title', { name: p.name }) : t('dash.titleFallback')}
          </div>
          <div className="page-sub">
            {p
              ? t('dash.sub', { age: p.age, city: p.city, risk: p.risk_tolerance })
              : t('dash.loading')}
          </div>
        </div>
        <Link to="/chat" className="btn btn-primary">
          {t('dash.cta')}
        </Link>
      </div>

      {standing && (
        <div style={{ marginBottom: 16 }}>
          <AlertBanner alert={standing} />
        </div>
      )}

      <div className="dash-grid">
        {p ? (
          <>
            <StatCard
              label={t('dash.salary')}
              value={sar(p.salary, lang)}
              meta={t('dash.salaryMeta', { surplus: sar(p.monthly_surplus, lang) })}
            />
            <StatCard
              label={t('dash.savings')}
              value={sar(p.savings, lang)}
              meta={t('dash.savingsMeta', { months: covered })}
            />
            <StatCard
              label={t('dash.expenses')}
              value={sar(p.monthly_expenses, lang)}
              meta={t('dash.expensesMeta', { debt: sar(p.monthly_debt, lang) })}
            />
          </>
        ) : (
          <>
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
          </>
        )}

        <HealthGauge health={data?.health} />
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <div className="panel-title">{t('dash.projTitle')}</div>
            <div className="panel-sub">
              {p
                ? t('dash.projSub', { surplus: sar(p.monthly_surplus, lang) })
                : t('dash.projLoading')}
            </div>
          </div>
          <div className="legend">
            <span>
              <i style={{ background: CHART.savings }} />
              {t('chart.savings')}
            </span>
            <span>
              <i style={{ background: CHART.income }} />
              {t('chart.income')}
            </span>
            <span>
              <i style={{ background: CHART.expenses, opacity: 0.35 }} />
              {t('chart.outgoings')}
            </span>
          </div>
        </div>

        <TimelineChart data={timeline?.timeline} floor={floor} height={280} />
      </div>

      <div className="two-col">
        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">{t('dash.goals')}</div>
            <div className="panel-sub">{t('dash.goalsSub')}</div>
          </div>

          {p ? (
            p.goals.map((g) => {
              // Money you'd have to raid the emergency fund to spend is not progress.
              const investable = Math.max(0, p.savings - floor)
              const pct = Math.min(100, (investable / g.amount) * 100)
              return (
                <div className="goal-row" key={g.name}>
                  <div className="goal-name">
                    <b>{g.name}</b>
                    <span>
                      {sar(g.amount, lang)}
                      {g.horizon_months
                        ? ` · ${t('dash.goalHorizon', { months: g.horizon_months })}`
                        : ''}
                    </span>
                  </div>
                  <div className="goal-bar">
                    <i style={{ width: `${pct}%` }} />
                  </div>
                  <div className="goal-pct num">{Math.round(pct)}%</div>
                </div>
              )
            })
          ) : (
            <div className="skeleton" style={{ height: 60 }} />
          )}

          {p?.liabilities?.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div className="panel-title" style={{ fontSize: 15, marginBottom: 10 }}>
                {t('dash.liabilities')}
              </div>
              {p.liabilities.map((l) => (
                <div className="expense-row" key={l.name}>
                  <span className="expense-dot" style={{ background: CHART.floor }} />
                  <span className="label">{l.name}</span>
                  <span className="amt num">
                    {t('dash.liabilityMeta', {
                      amount: sar(l.monthly_payment, lang),
                      months: l.months_remaining,
                    })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-head">
            <div className="panel-title">{t('dash.spending')}</div>
            <div className="panel-sub">{t('dash.spendingSub')}</div>
          </div>

          {p ? (
            Object.entries(p.expense_breakdown).map(([name, amount], i) => (
              <div className="expense-row" key={name}>
                <span
                  className="expense-dot"
                  style={{ background: EXPENSE_COLOURS[i % EXPENSE_COLOURS.length] }}
                />
                <span className="label">{name}</span>
                <span className="amt num">{sar(amount, lang)}</span>
              </div>
            ))
          ) : (
            <div className="skeleton" style={{ height: 60 }} />
          )}
        </div>
      </div>
    </div>
  )
}
