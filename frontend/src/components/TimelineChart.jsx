import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useLang } from '../lib/i18n'
import { CHART, sar, sarShort } from '../lib/format'

/**
 * The 12-month projection.
 *
 * Savings is the story, so it gets the filled area; income and expenses are thin
 * reference lines behind it. The emergency-fund floor is drawn as a red dashed line  
 * the whole product is about whether the savings curve stays above it, so it has to be
 * visible at a glance.
 *
 * In RTL the chart mirrors properly: time runs right-to-left, the value axis moves to the
 * right edge, and the floor label anchors to the correct corner. A chart that keeps
 * running left-to-right inside an RTL page reads as a bug, not as a chart.
 */

function TwinTooltip({ active, payload, label }) {
  const { t, lang } = useLang()
  if (!active || !payload?.length) return null
  const row = payload[0].payload

  return (
    <div className="tooltip">
      <div className="tooltip-month">{label}</div>
      <div className="tooltip-row">
        <span>
          <i style={{ background: CHART.savings }} />
          {t('chart.savings')}
        </span>
        <b>{sar(row.savings, lang)}</b>
      </div>
      <div className="tooltip-row">
        <span>
          <i style={{ background: CHART.income }} />
          {t('chart.income')}
        </span>
        <b>{sar(row.income, lang)}</b>
      </div>
      <div className="tooltip-row">
        <span>
          <i style={{ background: CHART.expenses }} />
          {t('chart.outgoings')}
        </span>
        <b>{sar(row.expenses, lang)}</b>
      </div>

      {row.purchase > 0 && (
        <div className="tooltip-row">
          <span>{t('chart.purchase')}</span>
          <b>−{sar(row.purchase, lang)}</b>
        </div>
      )}

      {row.events?.map((e) => (
        <div className="tooltip-note event" key={e}>
          {e}
        </div>
      ))}
      {row.warnings?.map((w) => (
        <div className="tooltip-note warn" key={w}>
          ⚠ {w}
        </div>
      ))}
    </div>
  )
}

export default function TimelineChart({ data, floor, height = 260, animationKey }) {
  const { t, rtl } = useLang()

  if (!data?.length) {
    return <div className="skeleton" style={{ height, borderRadius: 12 }} />
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart
        data={data}
        // Leave room for the value axis on whichever side it lives.
        margin={{ top: 8, right: rtl ? -12 : 8, left: rtl ? 8 : -12, bottom: 0 }}
        // Remount when the language flips so the axes re-lay out cleanly.
        key={`${animationKey ?? 'chart'}-${rtl ? 'rtl' : 'ltr'}`}
      >
        <defs>
          <linearGradient id="savingsFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={CHART.savings} stopOpacity={0.28} />
            <stop offset="100%" stopColor={CHART.savings} stopOpacity={0.02} />
          </linearGradient>
        </defs>

        <CartesianGrid strokeDasharray="3 3" stroke="#EFE7E5" vertical={false} />

        <XAxis
          dataKey="month"
          // Time flows with the reading direction.
          reversed={rtl}
          tick={{ fontSize: 11, fill: '#8A8AA6' }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
          minTickGap={18}
        />
        <YAxis
          orientation={rtl ? 'right' : 'left'}
          tick={{ fontSize: 11, fill: '#8A8AA6' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={sarShort}
          width={52}
        />

        <Tooltip content={<TwinTooltip />} cursor={{ stroke: '#8A8AA6', strokeWidth: 1 }} />

        {/* The line the Twin exists to defend. */}
        {floor > 0 && (
          <ReferenceLine
            y={floor}
            stroke={CHART.floor}
            strokeDasharray="5 4"
            strokeWidth={1.5}
            label={{
              value: `${t('chart.floor')} · ${sarShort(floor)}`,
              position: rtl ? 'insideTopRight' : 'insideTopLeft',
              fill: CHART.floor,
              fontSize: 10.5,
              fontWeight: 600,
              offset: 8,
            }}
          />
        )}

        <Area
          type="monotone"
          dataKey="savings"
          stroke={CHART.savings}
          strokeWidth={2.5}
          fill="url(#savingsFill)"
          animationDuration={1100}
          animationEasing="ease-out"
          dot={false}
          activeDot={{ r: 5, strokeWidth: 2, stroke: '#fff' }}
        />
        <Line
          type="monotone"
          dataKey="income"
          stroke={CHART.income}
          strokeWidth={1.5}
          strokeDasharray="4 4"
          dot={false}
          animationDuration={1100}
        />
        <Line
          type="monotone"
          dataKey="expenses"
          stroke={CHART.expenses}
          strokeWidth={1.5}
          strokeOpacity={0.35}
          dot={false}
          animationDuration={1100}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
