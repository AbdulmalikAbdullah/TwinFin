import { useLang } from '../lib/i18n'
import { sar } from '../lib/format'

/**
 * One scenario, colour-coded by risk. Clicking it swaps the timeline chart below to that
 * scenario's projection — the comparison is the product, so it has to be one click.
 *
 * Every figure here comes from simulation.py, and so do `name`, `detail` and
 * `recommendation` — already in the right language. We never branch on `name`; the
 * scenario's stable `key` is what identifies it.
 */
export default function ScenarioCard({ scenario, selected, onSelect, index }) {
  const { t, lang } = useLang()
  const s = scenario
  const delta = s.health_delta
  const deltaClass = delta > 0.05 ? 'up' : delta < -0.05 ? 'down' : 'flat'

  return (
    <button
      className={`scenario${selected ? ' selected' : ''}`}
      data-risk={s.risk}
      onClick={() => onSelect(s)}
      style={{ animationDelay: `${index * 70}ms` }}
      aria-pressed={selected}
    >
      {s.recommended && <span className="scenario-badge">{t('scn.recommended')}</span>}

      <div className="scenario-head">
        <span className="scenario-name">{s.name}</span>
        <span className="risk-pill" data-risk={s.risk}>
          {t(`risk.${s.risk}`)}
        </span>
      </div>

      <div className="scenario-metrics">
        <div className="metric">
          <span className="metric-label">{t('scn.savingsLeft')}</span>
          <span className={`metric-value${s.remaining_savings < 0 ? ' bad' : ''}`}>
            {sar(s.remaining_savings, lang)}
          </span>
        </div>

        <div className="metric">
          <span className="metric-label">{t('scn.cashFlow')}</span>
          <span className={`metric-value${s.monthly_cash_flow < 0 ? ' bad' : ''}`}>
            {sar(s.monthly_cash_flow, lang)}
            {t('scn.perMonth')}
          </span>
        </div>

        <div className="metric">
          <span className="metric-label">{t('scn.emergencyFund')}</span>
          <span className={`metric-value${s.emergency_fund_ok ? '' : ' bad'}`}>
            {s.emergency_fund_months} {t('scn.mo')}
            {s.emergency_fund_ok ? '' : ' ⚠'}
          </span>
        </div>

        {s.monthly_payment > 0 && (
          <div className="metric">
            <span className="metric-label">{t('scn.installment')}</span>
            <span className="metric-value">
              {sar(s.monthly_payment, lang)}
              {t('scn.perMonth')}
            </span>
          </div>
        )}

        <div className="metric">
          <span className="metric-label">{t('scn.goalDelay')}</span>
          <span className="metric-value">
            {s.goal_delay_months === 0
              ? t('scn.none')
              : `${s.goal_delay_months} ${t('scn.mo')}`}
          </span>
        </div>

        <div className="metric">
          <span className="metric-label">{t('scn.healthScore')}</span>
          <span className="metric-value">
            {/* Force the score+delta to read left-to-right even in RTL: "85.7 −13.3" is a
                numeric expression, and mirroring it would put the sign in the wrong place. */}
            <bdi>
              {s.health_score}
              <span className={`delta ${deltaClass}`}>
                {delta > 0 ? '+' : ''}
                {delta.toFixed(1)}
              </span>
            </bdi>
          </span>
        </div>
      </div>

      <div className="scenario-foot">{s.recommendation}</div>
    </button>
  )
}
