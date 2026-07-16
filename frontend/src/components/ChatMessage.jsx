import { useState } from 'react'
import Markdown from 'react-markdown'
import AlertBanner from './AlertBanner'
import ScenarioCard from './ScenarioCard'
import TimelineChart from './TimelineChart'
import { useLang } from '../lib/i18n'
import { CHART, sar } from '../lib/format'

/**
 * One turn of the conversation.
 *
 * A Twin reply is not a blob of text: it is a verdict (alert), a set of costed options
 * (scenario cards), and a projection of the one you pick (chart). The prose explains the
 * numbers; the components *are* the numbers.
 */

export function TypingMessage() {
  const { t } = useLang()
  return (
    <div className="msg msg-twin">
      <div className="msg-avatar" />
      <div className="msg-body">
        <div className="msg-name">{t('chat.twin')}</div>
        <div className="typing" aria-label={t('chat.thinking')}>
          <i />
          <i />
          <i />
        </div>
      </div>
    </div>
  )
}

export default function ChatMessage({ message, emergencyFloor }) {
  const { t, lang } = useLang()
  const isUser = message.role === 'user'

  // Which scenario's projection is on the chart. Defaults to the recommended one.
  const scenarios = message.scenarios ?? []
  const recommended = scenarios.find((s) => s.recommended) ?? scenarios[0]
  const [pickedKey, setPickedKey] = useState(null)
  // Track the *key*, never the name — the name is a translated display string.
  const active = scenarios.find((s) => s.key === pickedKey) ?? recommended

  if (isUser) {
    return (
      <div className="msg msg-user">
        <div className="msg-avatar">{t('chat.you')}</div>
        <div className="msg-body">
          <div className="msg-name">{t('chat.you')}</div>
          <div className="prose">
            <p>{message.content}</p>
          </div>
        </div>
      </div>
    )
  }

  // A scenario carries its own 12-month projection, so switching cards needs no round trip.
  const chartData = active?.timeline ?? message.timeline ?? []

  return (
    <div className="msg msg-twin">
      <div className="msg-avatar" />
      <div className="msg-body">
        <div className="msg-name">{t('chat.twin')}</div>

        {message.error ? (
          <div className="error-box">{message.error}</div>
        ) : (
          <>
            {message.alert && (
              <div style={{ marginBottom: 16 }}>
                <AlertBanner alert={message.alert} />
              </div>
            )}

            <div className="prose">
              <Markdown>{message.content}</Markdown>
            </div>

            {scenarios.length > 0 && (
              <>
                <div className="scenarios">
                  {scenarios.map((s, i) => (
                    <ScenarioCard
                      key={s.key}
                      scenario={s}
                      index={i}
                      selected={active?.key === s.key}
                      onSelect={(picked) => setPickedKey(picked.key)}
                    />
                  ))}
                </div>

                {chartData.length > 0 && (
                  <div className="panel" style={{ marginTop: 14 }}>
                    <div className="panel-head">
                      <div>
                        <div className="panel-title">
                          {t('chart.projection', { name: active?.name })}
                        </div>
                        <div className="panel-sub">
                          {active?.detail || t('chart.compare')}
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

                    <TimelineChart
                      data={chartData}
                      floor={emergencyFloor}
                      height={240}
                      // Remounting on scenario change replays the draw animation, so the
                      // comparison reads as a transition rather than a jump cut.
                      animationKey={active?.key}
                    />

                    {active && (
                      <div className="panel-sub" style={{ marginTop: 12 }}>
                        {t('chart.endsAt')}{' '}
                        <b className="num">
                          {sar(chartData[chartData.length - 1]?.savings, lang)}
                        </b>
                        {' · '}
                        {t('chart.totalCost')}{' '}
                        <b className="num">{sar(active.total_cost, lang)}</b>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Source filenames are intentionally not shown to the user. The RAG passages
                still ground the answer on the backend — they are just not surfaced here. */}
          </>
        )}
      </div>
    </div>
  )
}
