# Hasila MVP

Hasila is an AI-powered financial twin MVP built with Next.js, FastAPI, LangChain, and ChromaDB. It demonstrates a personalized financial assistant that blends a financial profile, scenario simulation, and retrieval-augmented guidance.

## Structure
- frontend/: Next.js and Tailwind UI
- backend/: FastAPI API and RAG service
- knowledge/: Markdown documents for financial advice

## Run locally
1. Make sure your API key is available in the workspace environment file at .env.
   - The backend will read `groq_API` (or `GROQ_API_KEY`) automatically.
2. Install frontend dependencies:
   - cd frontend && npm install
3. Install backend dependencies:
   - cd backend && pip install -r requirements.txt
4. Start the backend:
   - uvicorn main:app --reload --host 0.0.0.0 --port 8000
5. Start the frontend:
   - cd frontend && npm run dev
