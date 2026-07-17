import { useEffect, useRef, useState } from 'react'
import ChatMessage, { TypingMessage } from '../components/ChatMessage'
import { getProfile, sendChat, transcribeAudio } from '../lib/api'
import { useLang } from '../lib/i18n'

/**
 * The demo script, as buttons   in whichever language is active. These are the questions
 * the Twin is built to answer, and they double as the fastest way to show what it does.
 */
const CHIP_KEYS = ['chat.chip1', 'chat.chip2', 'chat.chip3', 'chat.chip4', 'chat.chip5']

export default function Chat() {
  const { t, lang } = useLang()

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [floor, setFloor] = useState(0)

  // Voice input (Whisper STT on the backend). `micNote` doubles as the status/error line.
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [micNote, setMicNote] = useState('')

  const scrollRef = useRef(null)
  const textareaRef = useRef(null)
  const recorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)

  // Voice is a progressive enhancement: only offered where the browser can record.
  const micSupported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof window !== 'undefined' &&
    'MediaRecorder' in window

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

  // -- Voice input ---------------------------------------------------------------------
  // Record with the browser, send the blob to /api/transcribe, drop the text into the
  // composer for the user to review and send. The transcript is never auto-sent.

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  async function startRecording() {
    if (recording || transcribing || busy) return
    setMicNote('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []
      const recorder = new MediaRecorder(stream)
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = async () => {
        stopStream()
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        chunksRef.current = []
        if (!blob.size) return
        setTranscribing(true)
        setMicNote(t('chat.transcribing'))
        const res = await transcribeAudio(blob, lang)
        setTranscribing(false)
        if (res.error) {
          setMicNote(res.error)
        } else if (res.text) {
          // Send the moment we have the transcript   no review step.
          setMicNote('')
          ask(res.text)
        } else {
          setMicNote(t('chat.noSpeech'))
        }
      }
      recorderRef.current = recorder
      recorder.start()
      setRecording(true)
      setMicNote(t('chat.listening'))
    } catch {
      // Permission denied, no device, or an insecure context   all mean "just type".
      setMicNote(t('chat.micDenied'))
    }
  }

  function stopRecording() {
    const recorder = recorderRef.current
    if (recorder && recorder.state !== 'inactive') recorder.stop()
    setRecording(false)
  }

  const toggleMic = () => (recording ? stopRecording() : startRecording())

  // Release the mic if the user leaves the chat mid-recording.
  useEffect(() => {
    return () => {
      try {
        if (recorderRef.current && recorderRef.current.state !== 'inactive') {
          recorderRef.current.stop()
        }
      } catch {
        // Nothing to clean up if the recorder was never started.
      }
      stopStream()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function ask(text) {
    const question = text.trim()
    if (!question || busy) return

    // Only the plain text goes into history   the backend router needs the conversation,
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

          {micNote && <div className="mic-note">{micNote}</div>}

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
            {micSupported && (
              <button
                type="button"
                className={`mic${recording ? ' recording' : ''}`}
                onClick={toggleMic}
                disabled={busy || transcribing}
                aria-label={recording ? t('chat.micStop') : t('chat.micStart')}
                aria-pressed={recording}
                title={recording ? t('chat.micStop') : t('chat.micStart')}
              >
                {transcribing ? (
                  <span className="mic-spinner" aria-hidden="true" />
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" width="18" height="18" aria-hidden="true">
                    <rect
                      x="9"
                      y="3"
                      width="6"
                      height="11"
                      rx="3"
                      stroke="currentColor"
                      strokeWidth="1.9"
                    />
                    <path
                      d="M5.6 11a6.4 6.4 0 0 0 12.8 0M12 17.5V21M8.7 21h6.6"
                      stroke="currentColor"
                      strokeWidth="1.9"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </button>
            )}
            <button
              className="send"
              onClick={() => ask(input)}
              disabled={busy || transcribing || !input.trim()}
              aria-label={t('chat.send')}
            >
              {/* An upward arrow reads the same in both directions   no flip needed. */}
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
