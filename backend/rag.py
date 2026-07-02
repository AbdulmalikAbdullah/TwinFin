import csv
import os
import re
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

try:
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    from langchain_chroma import Chroma
    LLM_AVAILABLE = True
except Exception:  # pragma: no cover - fallback path for offline environments
    DirectoryLoader = None
    TextLoader = None
    RecursiveCharacterTextSplitter = None
    OpenAIEmbeddings = None
    Chroma = None
    Document = None
    LLM_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except Exception:  # pragma: no cover - fallback path for offline environments
    OpenAI = None
    OPENAI_AVAILABLE = False


class FinancialRAGService:
    def __init__(self, knowledge_dir: Optional[str] = None):
        self.knowledge_dir = Path(knowledge_dir or Path(__file__).resolve().parents[1] / 'knowledge')
        self._docs = []
        self._doc_sources = []
        self._retriever = None
        self._client = None
        self._load_documents()
        self._init_client()

    def _init_client(self) -> None:
        api_key = os.getenv('groq_API') or os.getenv('GROQ_API_KEY') or os.getenv('OPENAI_API_KEY')
        if not api_key or not OPENAI_AVAILABLE:
            self._client = None
            return
        try:
            self._client = OpenAI(api_key=api_key, base_url='https://api.groq.com/openai/v1')
        except Exception:
            self._client = None

    def _load_documents(self) -> None:
        if not self.knowledge_dir.exists():
            self._docs = []
            self._doc_sources = []
            return

        raw_documents: List[tuple[str, str]] = []
        for markdown_file in sorted(self.knowledge_dir.glob('*.md')):
            raw_documents.append((markdown_file.read_text(encoding='utf-8'), markdown_file.name))

        for csv_file in sorted(self.knowledge_dir.glob('*.csv')):
            with csv_file.open(encoding='utf-8', newline='') as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    if not row:
                        continue
                    payload = '; '.join(
                        f'{key}: {value}'
                        for key, value in row.items()
                        if value not in (None, '')
                    )
                    raw_documents.append((payload, csv_file.name))

        self._docs = [content for content, _ in raw_documents]
        self._doc_sources = [source for _, source in raw_documents]

        if LLM_AVAILABLE and Document is not None:
            try:
                langchain_docs = [
                    Document(page_content=content, metadata={'source': source})
                    for content, source in raw_documents
                ]
                splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=120)
                splits = splitter.split_documents(langchain_docs)
                embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
                vector_store = Chroma.from_documents(splits, embeddings, persist_directory=str(self.knowledge_dir / '.chroma'))
                self._retriever = vector_store.as_retriever(search_kwargs={'k': 3})
                self._docs = [doc.page_content for doc in splits]
                self._doc_sources = [Path(doc.metadata.get('source', 'knowledge')).name for doc in splits]
                return
            except Exception:
                pass

    def retrieve(self, query: str) -> List[dict]:
        if self._retriever is not None:
            try:
                docs = self._retriever.get_relevant_documents(query)
                return [
                    {
                        'content': doc.page_content,
                        'source': Path(doc.metadata.get('source', 'knowledge')).name,
                    }
                    for doc in docs
                ]
            except Exception:
                pass

        lowered = query.lower()
        scored = []
        query_tokens = set(re.findall(r'[a-z0-9]+', lowered))
        for content, source in zip(self._docs, self._doc_sources):
            content_lower = content.lower()
            score = 0
            if 'car' in lowered and 'car' in content_lower:
                score += 3
            if 'emergency' in lowered and 'emergency' in content_lower:
                score += 3
            if 'budget' in lowered and 'budget' in content_lower:
                score += 3
            if 'zakat' in lowered and 'zakat' in content_lower:
                score += 2
            if 'finance' in lowered and 'finance' in content_lower:
                score += 2
            if 'save' in lowered and 'save' in content_lower:
                score += 2

            content_tokens = set(re.findall(r'[a-z0-9]+', content_lower))
            overlap = len(query_tokens & content_tokens)
            if overlap:
                score += overlap

            customer_terms = ['customer', 'client', 'customers', 'clients', 'attrition', 'income', 'card', 'gender', 'education', 'marital', 'dependent', 'credit', 'utilization']
            customer_fields = ['client_num', 'attrition_flag', 'customer_age', 'income_category', 'card_category', 'education_level', 'marital_status', 'dependent_count', 'credit_limit', 'avg_utilization_ratio']
            if any(term in lowered for term in customer_terms):
                if any(field in content_lower for field in customer_fields):
                    score += 6
                if 'pattern' in lowered and 'attrition_flag' in content_lower:
                    score += 2

            if score > 0:
                scored.append((score, {'content': content, 'source': source}))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:3]]

    def _build_prompt(self, question: str, profile: dict, retrieved_context: str) -> str:
        return (
            'You are Tawam, an AI financial twin. Use the retrieved financial knowledge and the user profile to answer. '
            'Be specific, concise, and personalized. Do not invent facts.\n\n'
            f'Profile: salary {profile.get("salary", 0)} SAR, savings {profile.get("savings", 0)} SAR, '
            f'expenses {profile.get("expenses", 0)} SAR, emergency fund {profile.get("emergencyFund", 0)} SAR, '
            f'goal {profile.get("goal", "financial stability")}.\n\n'
            f'Retrieved knowledge:\n{retrieved_context}\n\n'
            f'User question: {question}\n\n'
            'Return a short answer that includes: a recommendation, 2-3 practical reasons, and the relevant source files by name.'
        )

    def _ask_llm(self, question: str, profile: dict, retrieved_context: str) -> Optional[str]:
        if not self._client:
            return None
        try:
            completion = self._client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are Tawam, a cautious and helpful financial twin focused on practical, personalized advice.',
                    },
                    {'role': 'user', 'content': self._build_prompt(question, profile, retrieved_context)},
                ],
                temperature=0.2,
                max_tokens=280,
            )
            return completion.choices[0].message.content.strip()
        except Exception:
            return None

    def build_response(self, question: str, profile: dict) -> dict:
        retrieved = self.retrieve(question)
        retrieved_context = '\n\n'.join(
            f"Source: {item['source']}\n{item['content']}" for item in retrieved[:3]
        )
        sources = [item['source'] for item in retrieved[:3] if item.get('source')]
        lower_q = question.lower()
        if 'car' in lower_q:
            recommendation = 'A car purchase should be delayed unless the monthly payment remains comfortably below your cash flow.'
        elif 'salary' in lower_q or 'decrease' in lower_q:
            recommendation = 'If salary drops, protect your emergency fund first and reduce discretionary expenses before considering financing.'
        elif 'wait' in lower_q or 'months' in lower_q:
            recommendation = 'Waiting gives you more flexibility and improves your chances of staying aligned with your housing goal.'
        else:
            recommendation = 'A calmer, slower path is usually better when the decision would weaken your savings buffer.'

        llm_answer = self._ask_llm(question, profile, retrieved_context)
        if llm_answer:
            answer = llm_answer
        else:
            dataset_excerpt = next(
                (item['content'] for item in retrieved if 'Client_Num' in item.get('content', '') or 'Attrition_Flag' in item.get('content', '')),
                None,
            )
            if dataset_excerpt:
                answer = (
                    f"Based on the customer data I retrieved, {dataset_excerpt[:500]}. "
                    f"Using that context, {recommendation} Your profile shows a salary of {profile.get('salary', 0)} SAR, savings of {profile.get('savings', 0)} SAR, monthly expenses of {profile.get('expenses', 0)} SAR, and an emergency fund of {profile.get('emergencyFund', 0)} SAR."
                )
            else:
                answer = (
                    f"Using your financial twin and the retrieved guidance, {recommendation} "
                    f"Your profile shows a salary of {profile.get('salary', 0)} SAR, savings of {profile.get('savings', 0)} SAR, monthly expenses of {profile.get('expenses', 0)} SAR, and an emergency fund of {profile.get('emergencyFund', 0)} SAR. "
                    f"The retrieved financial context came from: {', '.join(sources) if sources else 'the knowledge base'}."
                )
        insights = [
            'Your emergency reserve is strong enough to absorb a short pause.',
            'A cheaper alternative is the most balanced choice for this profile.',
            'The retrieved knowledge base supports a more conservative purchase decision.'
        ]
        return {
            'answer': answer,
            'insights': insights,
            'scenarios': [
                {'name': 'Buy Now', 'risk': 'High', 'recommendation': 'Avoid unless the purchase is essential.'},
                {'name': 'Wait 6 Months', 'risk': 'Medium', 'recommendation': 'Build flexibility and protect your goal timeline.'},
                {'name': 'Cheaper Alternative', 'risk': 'Low', 'recommendation': 'Best balance for savings and stability.'},
            ],
            'sources': sources,
        }
