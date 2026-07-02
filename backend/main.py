import os
from pathlib import Path
from typing import Any, List
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rag import FinancialRAGService

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GROQ_API_KEY = os.getenv('groq_API') or os.getenv('GROQ_API_KEY') or os.getenv('OPENAI_API_KEY')

app = FastAPI(title='التوأم API', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class FinancialProfile(BaseModel):
    salary: int
    savings: int
    expenses: int
    assets: int
    liabilities: int
    goal: str
    emergencyFund: int


class ChatRequest(BaseModel):
    question: str


class SimulateRequest(BaseModel):
    purchaseAmount: int = Field(..., description='Suggested purchase amount in SAR')
    delayMonths: int = Field(default=6, ge=0, le=24)


class ScenarioCard(BaseModel):
    name: str
    risk: str
    recommendation: str
    impact: int


class ChatResponse(BaseModel):
    answer: str
    insights: List[str]
    scenarios: List[ScenarioCard]
    profile: FinancialProfile
    timeline: List[dict[str, Any]]
    sources: List[str]


profile = FinancialProfile(
    salary=18000,
    savings=250000,
    expenses=9000,
    assets=420000,
    liabilities=115000,
    goal='Buy a house',
    emergencyFund=120000,
)

rag_service = FinancialRAGService()


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/config')
def config():
    return {
        'envFile': str(Path(__file__).resolve().parents[1] / '.env'),
        'groqConfigured': bool(GROQ_API_KEY),
        'provider': 'groq' if GROQ_API_KEY else 'none',
    }


@app.get('/profile', response_model=FinancialProfile)
def get_profile():
    return profile


@app.post('/simulate', response_model=List[ScenarioCard])
def simulate(request: SimulateRequest):
    monthly_flow = profile.salary - profile.expenses
    remaining_savings = profile.savings - request.purchaseAmount

    scenarios = [
        ScenarioCard(
            name='Buy Now',
            risk='High',
            recommendation='Avoid unless the purchase is essential and your emergency fund remains protected.',
            impact=-request.purchaseAmount,
        ),
        ScenarioCard(
            name='Wait 6 Months',
            risk='Medium',
            recommendation='A short delay improves liquidity and lowers the chance of derailing your housing goal.',
            impact=-(request.purchaseAmount // 2),
        ),
        ScenarioCard(
            name='Finance',
            risk='High',
            recommendation='Only consider financing if monthly instalments stay below 20% of your take-home income.',
            impact=-(request.purchaseAmount // 3),
        ),
        ScenarioCard(
            name='Cheaper Alternative',
            risk='Low',
            recommendation='The strongest option if you want to preserve savings and keep monthly cash flow stable.',
            impact=-(request.purchaseAmount // 4),
        ),
    ]

    if remaining_savings < profile.emergencyFund * 0.8:
        scenarios[0].recommendation = 'Pause and review before spending; your reserve would fall below a healthy threshold.'
    if monthly_flow < 8000:
        scenarios[2].recommendation = 'Financing is risky because your monthly cash flow is already constrained.'

    return scenarios


@app.get('/timeline', response_model=List[dict[str, Any]])
def timeline():
    values = []
    balance = profile.savings
    for idx in range(1, 13):
        balance = max(0, balance - 8000 + (3000 if idx % 3 == 0 else 0))
        values.append(
            {
                'month': f'M{idx}',
                'income': profile.salary,
                'expenses': profile.expenses + (500 if idx % 2 == 0 else 0),
                'balance': balance,
                'warning': 'Review spending' if balance < profile.emergencyFund * 0.7 else 'On track',
            }
        )
    return values


@app.post('/chat', response_model=ChatResponse)
def chat(request: ChatRequest):
    result = rag_service.build_response(request.question, profile.model_dump())
    scenarios = [
        ScenarioCard(
            name='Buy Now',
            risk='High',
            recommendation='Avoid unless the purchase is essential.',
            impact=-120000,
        ),
        ScenarioCard(
            name='Wait 6 Months',
            risk='Medium',
            recommendation='A short delay improves flexibility and protects your goal timeline.',
            impact=-60000,
        ),
        ScenarioCard(
            name='Cheaper Alternative',
            risk='Low',
            recommendation='Best balance of affordability and resilience.',
            impact=-45000,
        ),
    ]
    return ChatResponse(
        answer=result['answer'],
        insights=result['insights'],
        scenarios=scenarios,
        profile=profile,
        timeline=timeline(),
        sources=result.get('sources', []),
    )
