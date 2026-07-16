import { useEffect, useRef, useState } from 'react'
import ChatMessage, { TypingMessage } from '../components/ChatMessage'
import { getProfile, sendChat } from '../lib/api'
import { useLang } from '../lib/i18n'

/**
 * The demo script, as buttons — in whichever language is active. These are the questions
 * the Twin is built to answer, and they double as the fastest way to show what it does.
 */
const CHIP_KEYS = ['chat.chip1', 'chat.chip2', 'chat.chip3', 'chat.chip4', 'chat.chip5']

export default function Chat() {
  const { t, lang } = useLang()

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [floor, setFloor] = useState(0)

  const scrollRef = useRef(null)
  const textareaRef = useRef(null)

  // The emergency-fund line is a property of the profile, not of any one answer, so it is
  // fetched once and passed down to every chart.
  useEffect(() => {
    getProfile(lang).then((p) => {
      if (!p.error) setFloor(p.profile.emergency_fund_target)
    })
  }, [lang])

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, busy])

  const grow = (el) => {
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }

  async function ask(text) {
    const question = text.trim()
    if (!question || busy) return

    // Only the plain text goes into history — the backend router needs the conversation,
    // not the rendered components.
    const history = messages.map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setInput('')
    grow(textareaRef.current)
    setBusy(true)

    const response = await sendChat(question, history, lang)

    setMessages((prev) => [
      ...prev,
      response.error
        ? { role: 'assistant', content: '', error: response.error }
        : {
            role: 'assistant',
            content: response.answer,
            scenarios: response.scenarios,
            timeline: response.timeline,
            alert: response.alert,
            sources: response.sources,
            intent: response.intent,
          },
    ])
    setBusy(false)
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      ask(input)
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-scroll" ref={scrollRef}>
        <div className="container">
          {messages.length === 0 && !busy ? (
            <div className="chat-empty">
              <div className="brand-mark" />
              <h2>{t('chat.emptyTitle')}</h2>
              <p>{t('chat.emptySub')}</p>
            </div>
          ) : (
            <>
              {messages.map((m, i) => (
                <ChatMessage key={i} message={m} emergencyFloor={floor} />
              ))}
              {busy && <TypingMessage />}
            </>
          )}
        </div>
      </div>

      <div className="chat-foot">
        <div className="container">
          <div className="chips">
            {CHIP_KEYS.map((key) => (
              <button
                key={key}
                className="chip"
                onClick={() => ask(t(key))}
                disabled={busy}
              >
                {t(key)}
              </button>
            ))}
          </div>

          <div className="composer">
            <textarea
              ref={textareaRef}
              rows={1}
              value={input}
              placeholder={t('chat.placeholder')}
              onChange={(e) => {
                setInput(e.target.value)
                grow(e.target)
              }}
              onKeyDown={onKeyDown}
              disabled={busy}
            />
            <button
              className="send"
              onClick={() => ask(input)}
              disabled={busy || !input.trim()}
              aria-label={t('chat.send')}
            >
              {/* An upward arrow reads the same in both directions — no flip needed. */}
              <svg viewBox="0 0 24 24" fill="none" width="18" height="18" aria-hidden="true">
                <path
                  d="M12 19V5m-6.5 6.5L12 5l6.5 6.5"
                  stroke="currentColor"
                  strokeWidth="2.1"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
