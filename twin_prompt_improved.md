# Twin — AI Financial Twin (Hackathon MVP Build Prompt)

You are a senior AI engineer, full-stack developer, and UI/UX designer. Build a complete, runnable MVP web application called **Twin**. This is for a hackathon: the app must run locally with minimal setup, never crash during a live demo, and look premium. Prioritize a polished demo path over feature breadth.

---

## Vision

Twin is an AI-powered **Financial Twin** that simulates the future impact of a purchase *before* the user makes it, and proactively warns them about risky decisions.

Twin combines:
- A Financial Twin (the user's financial profile, mock data)
- A **deterministic financial simulation engine** (Python, not the LLM)
- A Retrieval-Augmented Generation (RAG) pipeline over a Saudi-context knowledge base
- A modern interactive dashboard with charts and scenario cards

---

## Architecture (non-negotiable rules)

1. **The LLM never does arithmetic.** All numbers (remaining savings, cash flow, goal delay, health score, 12-month projections) are computed by a Python simulation engine. The LLM receives the computed results as structured data and only explains them in natural language. This guarantees the numbers are always correct.
2. **Intent routing.** Every chat message is first classified:
   - `purchase_simulation` → extract `{item, price, financing_option?}` from the message using the LLM with structured/JSON output → run the simulation engine → retrieve RAG context → generate the answer.
   - `financial_question` (general advice) → RAG retrieval + Financial Twin context → generate answer.
   - `chitchat` → answer directly, briefly, no RAG.
3. **Grounded answers.** For the two financial intents, the final answer must combine: (a) retrieved knowledge-base passages, (b) the Financial Twin profile, (c) simulation results when applicable. (d) time line for the purchase item using diagram such as line graph and with the help of recharts.github.io to make Animated Time Series. 

4. **Structured API responses.** The backend returns JSON the frontend can render as components (schema below) — never markdown-only blobs.

---

## Tech Stack

**Frontend:** React (Vite), Recharts for charts, plain CSS or Tailwind.
**Backend:** Flask (Python), flask-cors enabled.
**LLM:** Groq API, model `llama-3.3-70b-versatile` (verify the current model id in the Groq console; make it configurable via env var `GROQ_MODEL`).
**RAG:** LangChain + ChromaDB (persistent local store).
**Embeddings:** OpenAI embeddings (`text-embedding-3-small`) if `OPENAI_API_KEY` is set; **automatic fallback** to local HuggingFace `sentence-transformers/all-MiniLM-L6-v2` if not. The app must work with only a Groq key.
**Config:** `.env` file loaded with python-dotenv. Provide `.env.example`.
**Dependencies:** Pin exact versions in `requirements.txt` and `package.json` (LangChain APIs change often — pinning prevents day-of-demo breakage).

---

## Mock Financial Twin (data/financial_twin.md)

Store one user profile in a Markdown file, parsed by the backend at startup:

```
name: Saad
age: 28
city: Riyadh
salary: 18000 SAR/month
savings: 500000 SAR
monthly_expenses: 9000 SAR
expense_breakdown:
  rent: 3500
  food: 1800
  transport: 900
  subscriptions: 300
  other: 2500
assets:
  - Investment account: 40000 SAR
liabilities:
  - Personal loan: 1200 SAR/month, 18 months remaining
emergency_fund_target: 6 months of expenses (54000 SAR)
goals:
  - Buy a car (~120000 SAR) within 12 months
  - Umrah trip: 8000 SAR
risk_tolerance: moderate
```

**Financial Health Score (0–100, computed in Python, show the formula in code comments):**
- Savings rate = (salary − expenses − liabilities) / salary → 40 pts
- Emergency fund coverage = savings vs. 6-month target, capped → 30 pts
- Debt-to-income ratio (lower is better) → 20 pts
- Goal progress → 10 pts

---

## Simulation Engine (backend/simulation.py)

Pure Python, fully deterministic, unit-testable. For a purchase of price `P`, generate these scenarios:

1. **Buy Now** — pay cash from savings.
2. **Wait 6 Months** — keep saving monthly surplus, then buy.
3. **Finance** — model a simple murabaha-style installment (e.g., 5% flat profit rate, 36 months — constants in config); show both the Islamic financing option and note the conventional equivalent.
4. **Cheaper Alternative** — 65% of the asked price.

For each scenario compute:
- Remaining savings after purchase
- New monthly cash flow
- Emergency fund status (months covered; flag if below target)
- Risk level: `low / medium / high` (rule-based: e.g., high if savings drop below emergency fund target or cash flow < 10% of salary)
- Estimated delay to the user's primary goal (months)
- One-line rule-based recommendation string

Also generate a **12-month timeline projection** (per scenario or for the recommended scenario): month, income, expenses, savings balance, warnings (e.g., "Savings dip below emergency fund in March"), events (e.g., "Loan ends in month 18 — excluded; car purchased in month 6").

**Proactive Alerts:** if any requested purchase would push savings below the emergency fund target or make cash flow negative, the API response includes an `alert` object; the UI renders it as a prominent warning banner. This is the "Twin protects you" moment — make it visually striking.

---

## RAG Pipeline

- `knowledge/` folder with 7 Markdown files, each 300–500 words of practical advice with Saudi-specific context: `budgeting.md`, `emergency_fund.md`, `car_financing.md` (include murabaha vs. conventional loans, typical Saudi bank terms), `zakat.md` (2.5% on eligible savings — mention how a large purchase affects zakat base), `islamic_finance.md`, `saving_strategies.md`, `financial_planning.md`.
- One-time ingest script `backend/ingest.py`: load Markdown files → split (RecursiveCharacterTextSplitter, ~500 chars, 50 overlap) → embed → persist to ChromaDB. Runs once; the server only reads the persisted store (fast startup, no re-embedding every run).
- Retriever: top-k = 3 with similarity scores. Include retrieved chunks + filenames in the LLM prompt.

---

## API Contract

`POST /api/chat` → request `{ "message": string, "history": [...] }` 

→ response:

```json
{
  "intent": "purchase_simulation | financial_question | chitchat",
  "answer": "natural-language answer, personalized, mentions Saad's actual numbers",
  "scenarios": [
    {
      "name": "Buy Now",
      "remaining_savings": 130000,
      "monthly_cash_flow": 7800,
      "emergency_fund_months": 14.4,
      "emergency_fund_ok": true,
      "risk": "low",
      "goal_delay_months": 0,
      "recommendation": "..."
    }
  ],
  "timeline": [
    { "month": "Aug 2026", "income": 18000, "expenses": 9000, "savings": 139000, "warnings": [], "events": [] }
  ],
  "alert": { "level": "warning", "message": "..." } 
}
```

`scenarios`, `timeline`, and `alert` are null/empty for non-purchase intents.
Also provide `GET /api/profile` (Financial Twin + health score) and `GET /api/timeline` (baseline 12-month projection for the dashboard).

**Error handling:** every endpoint wrapped in try/except; if Groq or embeddings fail, return a graceful JSON error the UI shows as a friendly message — the app must never show a blank screen or stack trace during the demo.

---

## Frontend — 3 polished pages

1. **Landing** — hero with the Twin value proposition ("Ask your Twin before you spend"), one CTA to the dashboard, subtle animation.
2. **Dashboard** — profile cards (salary, savings, expenses, goal, animated Financial Health Score gauge), the 12-month baseline timeline chart (Recharts area/line), and the alert banner area.
3. **Chat** — ChatGPT-style interface. When the response includes scenarios, render **comparison cards inline in the chat** (side by side, risk color-coded, recommended one highlighted); render the scenario timeline as a chart under the cards; Include 3–4 suggested question chips above the input ("What if I buy a car for 120,000 SAR?", "Can I afford a 300 SAR/month subscription?", "What if I wait six months?", "What happens if my salary drops 20%?") — these double as the demo script.

Loading states everywhere (skeletons/typing indicator). Chat answers render markdown.

---

## UI Design

Premium fintech aesthetic — minimal, modern, glassmorphism, rounded cards, soft shadows, smooth transitions, fully responsive.

- Background `#FFFFFF` · Primary `#D8653B` · Secondary `#8685D8` · Dark `#212145` · Dark Secondary `#313157` · Surface `#EFE7E5`
- Risk colors: low = green tint, medium = `#D8653B` tint, high = red tint.

---

## Deliverables

- Complete project structure (backend/, frontend/, knowledge/, data/)
- Flask backend: routes, intent router, simulation engine, RAG chain
- `backend/ingest.py` seed script
- React frontend: all 3 pages + reusable components (ScenarioCard, TimelineChart, HealthGauge, AlertBanner, ChatMessage)
- `.env.example` (GROQ_API_KEY, GROQ_MODEL, OPENAI_API_KEY optional)
- `requirements.txt` and `package.json` with pinned versions
- `README.md` with exact setup steps: install deps → run ingest → start backend → start frontend, plus the 4 demo questions
- Clean, commented, production-quality code

## Acceptance criteria (verify before finishing)

- [ ] Runs with only a Groq key (embeddings fall back to local model)
- [ ] "What if I buy a car for 120,000 SAR?" returns 4 scenario cards with mathematically correct numbers (verifiable by hand from the profile)
- [ ] Scenario numbers come from `simulation.py`, not the LLM
- [ ] Answer cites at least one knowledge-base source
- [ ] A purchase that breaks the emergency fund triggers the alert banner
- [ ] Dashboard health score and timeline load from the API
- [ ] No crash on API failure — graceful error message instead
