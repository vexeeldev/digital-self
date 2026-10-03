# 🧠 Digital Self

**Digital Self** is a full-stack personal knowledge graph & associative memory system. It ingests raw personal experiences, extracts canonical nodes & associations via LLM, persists them in PostgreSQL, and renders an interactive 2D/3D knowledge graph in Next.js.

---

## 🚀 System Architecture

- **Frontend**: Next.js (App Router), ReactFlow, Tailwind CSS, Lucide Icons, Three.js / React Force Graph 3D
- **Backend (Brain)**: Python FastAPI, Pydantic, Psycopg2, Antigravity LLM Provider (Gemini / Local LLM)
- **Database**: PostgreSQL (`digital_self` database)

---

## 🛠️ Getting Started

### 1. Database Setup
Ensure PostgreSQL is running locally and database `digital_self` exists:
```bash
createdb digital_self
```

### 2. Backend (Brain Engine) Setup
```bash
cd brain
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to open the interactive Digital Self interface.

---

## 📌 Features

- **Semantic Memory Ingestion**: Extracts entities, concepts, actions, emotions, and events.
- **Entity Resolution**: Canonical mapping to prevent duplicate nodes.
- **Associative Knowledge Graph**: Connects related memories into a dynamic neural network centered around `aku`.
- **Live Memory Stream**: Manage, filter, and inspect past experiences.
