from pathlib import Path

from rag import FinancialRAGService


def test_retrieval_returns_relevant_documents():
    knowledge_dir = Path(__file__).resolve().parents[1] / '..' / 'knowledge'
    service = FinancialRAGService(knowledge_dir=str(knowledge_dir))

    documents = service.retrieve('car financing')

    assert documents
    contents = [doc['content'] for doc in documents]
    joined = ' '.join(contents).lower()
    assert 'car' in joined or 'financing' in joined


def test_build_response_includes_sources():
    knowledge_dir = Path(__file__).resolve().parents[1] / '..' / 'knowledge'
    service = FinancialRAGService(knowledge_dir=str(knowledge_dir))

    response = service.build_response(
        'Should I buy a car now?',
        {'salary': 18000, 'savings': 250000, 'expenses': 9000, 'emergencyFund': 120000},
    )

    assert response['sources']
    assert any('car_financing' in source.lower() or 'budgeting' in source.lower() for source in response['sources'])


def test_customer_dataset_is_retrieved_for_customer_questions():
    knowledge_dir = Path(__file__).resolve().parents[1] / '..' / 'knowledge'
    service = FinancialRAGService(knowledge_dir=str(knowledge_dir))

    documents = service.retrieve('customer attrition income card category')

    assert documents
    joined = ' '.join(doc['content'] for doc in documents).lower()
    assert 'attrited customer' in joined or 'income category' in joined or 'card_category' in joined
