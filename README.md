# PaperFlow AI

AI-powered research workspace — local-first, private by design.

## 🌐 Live Demo
**https://idarragaa21-prog.github.io/paperflow-ai/**

> Demo mode: sign in with any email/password to explore the UI.

## Stack
- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI + PostgreSQL + Redis + Qdrant + Ollama
- **Local**: runs entirely on localhost, no cloud required

## Features
- 📚 Paper library with AI processing
- 🔍 PubMed search & reader
- 📊 Meta-analysis & data extraction
- 📝 Literature drafts & references
- 🏥 Clinical evidence sheets
- 📖 Books & document scanner
- 📱 Mobile responsive

## Run locally
```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173
```
