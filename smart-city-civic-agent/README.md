# Smart City Citizen Service Chatbot — Multimodal RAG-Enabled Civic Digital Agent

An end-to-end **Civic Digital Agent** designed for smart urban governance. Unlike static FAQ chatbots, this platform unifies **citation-backed municipal policy intelligence (RAG)**, **multimodal 311 grievance triage (Vision-Language classification)**, **PostgreSQL/PostGIS 50-meter geospatial deduplication**, **automated life-safety hazard escalation**, and an **RBAC Municipal Officer Dashboard**.

---

## Core Architecture & Features

1. **Citation-Backed Municipal RAG Engine (`backend/services/rag_engine.py`)**
   - Indexes municipal bylaws, property tax codes, trade license rules, water supply charters, and transit schedules in **Qdrant**.
   - Enforces inline clause-level citations (`[1] Document Title, Sec. X (p. Y)`) and deterministic abstention guardrails when queries fall outside official records.
2. **Stateful LangGraph Agentic Orchestrator (`backend/services/agent_orchestrator.py`)**
   - Routes citizen intents across policy inquiries, utility bill lookups, ticket status tracking, and guided 311 grievance filing.
3. **Multimodal Vision Triage (`backend/services/vision_triage.py`)**
   - Uses **Gemini 2.5 Flash** structured JSON output to verify that citizen-uploaded photographs depict genuine civic issues, classify the responsible municipal department (`ROADS`, `WASTE`, `WATER`, `EMERGENCY`), and assign severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
4. **PostGIS 50m / 48h Geospatial Deduplication (`backend/services/geo_dedup.py`)**
   - Executes `ST_DWithin` spatial-temporal queries (`50.0` meters, `48 hours`) inside serializable transactions to merge duplicate neighborhood reports into community upvotes while routing `CRITICAL` hazards (exposed electrical wires, open manholes, severe flooding) for immediate dispatch.
5. **Omnichannel Citizen UX & Municipal Officer Portal (`frontend/`)**
   - React + TypeScript + Tailwind CSS + Leaflet frontend featuring a Citizen Chat interface (with photo upload, GPS pin, and Web Speech voice input) and an RBAC Officer Dashboard with live severity markers and status management.

---

## Repository Structure

```text
smart-city-civic-agent/
├── docker-compose.yml              # PostgreSQL 16 + PostGIS 3.4, Qdrant, Redis 7
├── .env.example                    # Environment configuration template
├── db/
│   └── schema.sql                  # PostGIS tables, GIST spatial indexes & seed data
├── backend/
│   ├── requirements.txt            # Python dependencies
│   ├── ingest_policies.py          # Municipal bylaws & PDF vector ingestion script
│   ├── sample_data/
│   │   └── municipal_bylaws.json   # Structured municipal policy corpus
│   ├── services/
│   │   ├── rag_engine.py           # Qdrant + Gemini citation-grounded RAG
│   │   ├── vision_triage.py        # Multimodal VLM grievance verification
│   │   ├── geo_dedup.py            # PostGIS 50m/48h deduplication & SLA engine
│   │   └── agent_orchestrator.py   # LangGraph multi-turn agent & tool router
│   └── main.py                     # FastAPI gateway & REST endpoints
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── App.tsx
        ├── api.ts
        ├── types.ts
        └── components/
            ├── CitizenChat.tsx     # Citizen conversational UI + 311 multimodal intake
            └── AdminDashboard.tsx  # Officer map, cluster heatmap & SLA status manager
```

---

## Quick-Start Guide

### 1. Start Databases (PostgreSQL + PostGIS, Qdrant, Redis)
```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
docker compose up -d
```

### 2. Configure & Run FastAPI Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Ingest sample municipal bylaws into Qdrant
python ingest_policies.py

# Start API server
uvicorn main:app --reload --port 8000
```
API docs will be live at `http://localhost:8000/docs`.

### 3. Configure & Run React Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser to access both the **Citizen Service Portal** and the **Municipal Officer Portal** (default demo officer token: `officer-demo-token`).
