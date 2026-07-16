# Twin — your AI Financial Twin

**Ask your Twin before you spend.**

Twin simulates what a purchase actually does to your future — your savings, your monthly
breathing room, your emergency fund, and how far it pushes back the goals you already said
mattered — *before* you buy, and warns you when a decision is about to hurt.

Built for a Saudi context: murabaha vs. conventional financing, zakat, SAMA-regulated bank
terms, and a knowledge base written around them.

---

## The one architectural rule

> **The LLM never does arithmetic.**

Every number in the product — remaining savings, cash flow, emergency-fund cover, goal
delay, the health score, the 12-month projection — is computed by a deterministic Python
engine (`backend/simulation.py`). The language model receives those figures as structured
data and is only allowed to *explain* them.

This is why the numbers are always right, and why 29 unit tests can assert them by hand.
It is also why **Twin still works with no API key at all**: strip the LLM away and the
routing falls back to rules, the prose falls back to templates, and every figure on screen
is identical.

---

## Setup

Requires **Python 3.11+** and **Node 18+**.

```bash
# 1. Backend dependencies
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

# 2. Your Groq key
cp .env.example .env              # then paste your key into .env
                                  # free key: https://console.groq.com/keys

# 3. Build the knowledge base (once — takes ~30s, downloads the local embedding model)
python backend/ingest.py

# 4. Start the backend  (http://127.0.0.1:5000)
python backend/app.py

# 5. Start the frontend, in a second terminal  (http://localhost:5173)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

> The backend takes ~10 seconds to start the first time — it is loading the local embedding
> model. Wait for `Running on http://127.0.0.1:5000` before opening the UI.

### Before you present

```bash
python backend/demo_check.py      # runs the whole demo script and prints what judges will see
python -m pytest backend/tests -q # 29 tests, all hand-verifiable from the profile
```

---

## The demo script

| # | Ask | What it shows |
|---|-----|---------------|
| 1 | **What if I buy a car for 120,000 SAR?** | Four costed scenarios. He can afford it — Twin says *buy it* and doesn't manufacture a problem. |
| 2 | **What if I buy a car for 220,000 SAR?** | 🔴 The alert fires. It would leave 30,000 SAR against a 54,000 SAR floor. Financing is *worse* — it craters his health score from 99 to 55. Twin recommends the low-risk option instead. |
| 3 | **Can I afford a 300 SAR/month subscription?** | A recurring commitment isn't a purchase: it doesn't dent savings, it permanently narrows cash flow. Different scenarios, same cards. |
| 4 | **What if I wait six months?** | A follow-up with no price in it. Twin resolves "it" from the conversation. |
| 5 | **What happens if my salary drops 20%?** | An income shock, not a purchase. The best move isn't austerity — it's clearing the loan, which lands him at 100/100. |

**Question 2 is the money shot.** It is the "Twin protects you" moment: the product refuses
to endorse a high-risk route when a safe one exists.

---

## How a message is answered

```
message
   ↓
1. INTENT ROUTER  (LLM, JSON mode → falls back to regex rules)
   purchase_simulation  ·  financial_question  ·  chitchat
   ↓ extracts {item, price, recurring, financing_option, income_change_pct}
   ↓
2. SIMULATION ENGINE  (pure Python — this is where every number comes from)
   4 scenarios · 12-month projection each · risk · health score · alert
   ↓
3. RAG RETRIEVAL  (LangChain + ChromaDB, top-3 with scores)
   ↓
4. ANSWER  (LLM, given the profile + passages + computed figures → falls back to templates)
```

The response is structured JSON the frontend renders as components — never a markdown blob.

---

## Verifying the numbers by hand

From `data/financial_twin.md`: salary 18,000 · expenses 9,000 · loan 1,200/mo · savings
250,000.

```
monthly surplus         18,000 − 9,000 − 1,200            =   7,800 SAR
emergency fund target   6 × 9,000                         =  54,000 SAR

"Buy a car for 120,000 SAR" → Buy Now:
  remaining savings     250,000 − 120,000                 = 130,000 SAR
  emergency cover       130,000 ÷ 9,000                   =    14.4 months
  cash flow             unchanged                         =   7,800 SAR   →  low risk

"…for 220,000 SAR" → Buy Now:
  remaining savings     250,000 − 220,000                 =  30,000 SAR   ← below 54,000
  emergency cover       30,000 ÷ 9,000                    =     3.3 months →  HIGH risk

"…for 220,000 SAR" → Finance (murabaha, 5% flat, 36 months):
  monthly payment       220,000 × 1.05 ÷ 36               = 6,416.67 SAR
  cash flow             7,800 − 6,416.67                  = 1,383.33 SAR  ← under 10% of salary
  debt-to-income        (1,200 + 6,416.67) ÷ 18,000       =     42%       →  HIGH risk
```

Every one of those lines is asserted in `backend/tests/test_simulation.py`.

### The Financial Health Score (0–100)

A weighted sum, all four components computed in `simulation.health_score()`:

| Component | Weight | Full marks at |
|---|---|---|
| Savings rate | 40 | ≥ 20% of salary survives the month |
| Emergency fund coverage | 30 | ≥ 6 months of expenses in cash (capped) |
| Debt-to-income | 20 | ≤ 5% (zero at ≥ 40%) |
| Goal progress | 10 | primary goal funded from savings *above* the buffer |

Saad scores **99** today. The interesting number is never the score — it's what a decision
*does* to it. Financing a 220,000 SAR car takes him to **55**.

---

## Arabic & RTL

Toggle the language in the nav bar (**العربية / English**). The choice persists across
reloads and defaults to the browser's language.

The layout is not "translated" — it is **mirrored**. Setting `dir="rtl"` on `<html>` flips
the entire page, because the CSS is written with logical properties (`inset-inline`,
`margin-inline`, `text-align: end`) rather than a parallel set of RTL overrides. The
timeline chart mirrors too: time runs right-to-left and the value axis moves to the right
edge.

The part that matters most is deeper than the UI. **The simulation engine writes prose** —
scenario names, the one-line verdicts, the alert messages, the timeline events — so all of
that is localised in Python (`backend/i18n.py`), not bolted on in React. The LLM is told
which language to answer in; it is *not* asked to translate anything, because it never had
the numbers in the first place.

The contract is narrow and enforced by tests:

> **The words change. The numbers do not.**

`backend/tests/test_i18n.py` runs the same simulations in both languages and asserts every
computed figure is identical while every user-visible string differs. Two details worth
knowing:

- **Latin digits are kept in Arabic** (`120,000 ريال`, not `١٢٠٬٠٠٠`). That is what Saudi
  banking apps do, and it keeps the figures checkable against the English view at a glance.
- **The knowledge base stays English.** The local embedding model only speaks English, so an
  Arabic question is *searched* in English (the router emits an English `topic_en` for
  retrieval) and *answered* in Arabic, citing the English source filename. Retrieval quality
  is therefore identical in both languages.

Arabic also works with **no Groq key at all**: the rule-based router understands Arabic
prices ("120 ألف"), recurring costs ("300 ريال شهريًا") and salary shocks
("انخفض راتبي بنسبة 20%"), and the template writer replies in Arabic.

To add a third language: add its column to `STRINGS` in `backend/i18n.py`, add an
`xx_labels` block to `data/financial_twin.md`, and add its column to
`frontend/src/lib/strings.js`.

---

## Project layout

```
backend/
  app.py            Flask API — every route wrapped, never leaks a stack trace
  router.py         intent routing + answer generation (+ deterministic fallbacks)
  simulation.py     THE ENGINE. Pure Python, no I/O, fully unit-tested
  twin_profile.py   parses data/financial_twin.md
  rag.py            LangChain + Chroma retrieval, 3-tier embedding fallback
  ingest.py         one-time: knowledge/*.md → chunks → embeddings → Chroma
  llm.py            Groq client (REST, with retry on rate limits)
  config.py         every tunable constant in the financial model
  demo_check.py     preflight — run the whole demo script from the CLI
  tests/            29 tests, all hand-verifiable
frontend/
  src/pages/        Landing · Dashboard · Chat
  src/components/   ScenarioCard · TimelineChart · HealthGauge · AlertBanner · ChatMessage
knowledge/          7 Markdown files — the RAG corpus (Saudi-specific)
data/
  financial_twin.md the user profile. Edit this to change the demo — no code changes.
```

---

## Configuration

`.env` (see `.env.example`):

| Variable | Required | Notes |
|---|---|---|
| `GROQ_API_KEY` | no* | Without it Twin runs in deterministic-fallback mode — all numbers identical, prose templated. |
| `GROQ_MODEL` | no | Defaults to `llama-3.3-70b-versatile`. **Verify this id in the Groq console** — retired model names are the single likeliest thing to break on demo day. |
| `OPENAI_API_KEY` | no | If set, embeds with `text-embedding-3-small`. If not, uses the local MiniLM model. |

Check what's actually live: **`GET /api/health`** reports the LLM mode, the embedding
backend, and whether the knowledge base has been ingested.

### Embeddings degrade in three tiers

1. **OpenAI** `text-embedding-3-small` — if `OPENAI_API_KEY` is set
2. **Local HuggingFace** `all-MiniLM-L6-v2` — no key needed (this is the default)
3. **Built-in hashing embeddings** — pure Python, zero dependencies, always works

Tier 3 exists so that a missing model download can never kill the demo.

---

## Nothing here can show a blank screen

- Every Flask route is wrapped; failures return friendly JSON, not a traceback.
- Groq down, rate-limited, or unconfigured → rules + templates take over. The user still
  gets correct numbers and a real answer.
- Knowledge base not ingested → answers still work, just without citations.
- Backend not running → the UI says so, in words, with the command to fix it.

---

## API

| Endpoint | Returns |
|---|---|
| `POST /api/chat` | `{intent, answer, scenarios[], timeline[], alert, sources[]}` |
| `GET /api/profile` | the Financial Twin + health score and its four components |
| `GET /api/timeline` | the baseline 12-month projection |
| `GET /api/health` | LLM mode, embedding backend, ingest status |

`scenarios`, `timeline` and `alert` are empty/null for non-purchase intents. Each scenario
carries **its own 12-month projection**, so clicking between cards in the chat re-draws the
chart with no round trip.

---

## Tech

React (Vite) · Recharts · Flask · Groq (`llama-3.3-70b-versatile`) · LangChain · ChromaDB ·
sentence-transformers

All versions pinned in `requirements.txt` and `package.json` — LangChain's APIs move fast,
and pinning is what stops a fresh `pip install` from breaking a working app.
