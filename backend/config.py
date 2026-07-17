"""Central configuration for Twin.

Every tunable constant used by the simulation engine lives here so that the financial
model can be audited and adjusted in one place. Nothing in this module reads the LLM;
these are the levers of the deterministic engine.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project layout ----------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
DATA_DIR = ROOT_DIR / "data"
KNOWLEDGE_DIR = ROOT_DIR / "knowledge"
CHROMA_DIR = BACKEND_DIR / "chroma_db"
PROFILE_PATH = DATA_DIR / "financial_twin.md"

load_dotenv(ROOT_DIR / ".env")

# LLM ---------------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_TIMEOUT_SECONDS = 30

# Embeddings --------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_EMBED_MODEL = "text-embedding-3-small"
HF_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Speech-to-text ----------------------------------------------------------------------
# Whisper via faster-whisper, on CPU. "tiny" is the multilingual model (Arabic + English);
# do NOT use "tiny.en", which is English-only. int8 keeps it fast and light on CPU.
STT_MODEL = os.getenv("STT_MODEL", "tiny").strip()
STT_DEVICE = os.getenv("STT_DEVICE", "cpu").strip()
STT_COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8").strip()

# RAG ---------------------------------------------------------------------------------
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RETRIEVER_TOP_K = 3
COLLECTION_NAME = "twin_knowledge"

# Simulation engine -------------------------------------------------------------------
# Murabaha (Islamic cost-plus) financing. The bank buys the asset and resells it at a
# disclosed markup; the total repayable is fixed on day one and cannot grow.
# The markup is applied ONCE over the whole term, not per year:
#   120,000 SAR at 5% over 36 months -> 6,000 profit, 126,000 total, 3,500/month.
MURABAHA_FLAT_PROFIT_RATE = 0.05
MURABAHA_TERM_MONTHS = 36
# A conventional (riba-based) loan charges compounding interest on a declining balance.
# This is a typical Saudi market auto-loan APR, used only to price the comparison shown
# alongside the murabaha card so the user can see both totals.
CONVENTIONAL_EFFECTIVE_APR = 0.055

WAIT_MONTHS = 6  # horizon for the "Wait 6 Months" scenario
CHEAPER_ALTERNATIVE_RATIO = 0.65  # "Cheaper Alternative" = 65% of the asked price
EMERGENCY_FUND_MONTHS = 6  # target buffer = 6 months of expenses
TIMELINE_MONTHS = 12  # projection horizon

# Risk thresholds. A scenario is HIGH risk if it breaks the emergency fund or leaves the
# user with almost no monthly slack; MEDIUM if it materially erodes either.
MIN_CASH_FLOW_RATIO_HIGH = 0.10  # cash flow below 10% of salary -> high risk
MIN_CASH_FLOW_RATIO_MEDIUM = 0.25  # cash flow below 25% of salary -> medium risk
EF_RATIO_MEDIUM = 1.5  # savings below 1.5x the EF target -> medium risk

# Financial health score weights (must sum to 100). See simulation.health_score().
HEALTH_WEIGHT_SAVINGS_RATE = 40
HEALTH_WEIGHT_EMERGENCY_FUND = 30
HEALTH_WEIGHT_DEBT_TO_INCOME = 20
HEALTH_WEIGHT_GOAL_PROGRESS = 10

# Benchmarks used to normalise each health component onto a 0..1 scale.
HEALTHY_SAVINGS_RATE = 0.20  # a 20% savings rate earns full marks
DTI_EXCELLENT = 0.05  # debt-to-income at or below 5% earns full marks
DTI_FAILING = 0.40  # debt-to-income at or above 40% earns zero

# Zakat --------------------------------------------------------------------------------
ZAKAT_RATE = 0.025  # 2.5% on eligible (zakatable) wealth held for a lunar year
