# SVG Video Generator From Audio

> **Speak a technical concept. Watch an accurate, animated diagram build itself.**

An agentic system that turns a spoken (or typed) explanation into a **deterministic, editable, animated SVG diagram**. Instead of asking an LLM to draw pixels, the LLM emits a controlled **Scene DSL** (objects, connections, timeline), and a deterministic renderer animates it with GSAP. This gives pixel-level control and reproducible output — the opposite of black-box AI video generation.

```
🎙️ Voice ─► 📝 Transcribe (Whisper) ─► 🧠 LLM Gateway ─► 📐 Scene DSL ─► ✅ Validate/Repair ─► 🎬 GSAP + SVG ─► 📺 Live animation
```

## Why a Scene DSL?

Letting an LLM emit raw SVG animation code is unreliable. Instead the LLM produces a small, validated JSON document describing **what** should happen:

```jsonc
{
  "title": "Kubernetes pod failure",
  "objects": [
    { "id": "service", "type": "kubernetes.service", "label": "Service", "position": { "x": 640, "y": 90 } },
    { "id": "pod-1",   "type": "kubernetes.pod",     "label": "Pod 1",   "position": { "x": 300, "y": 420 } }
  ],
  "edges": [
    { "id": "e1", "from": "service", "to": "pod-1", "style": "traffic" }
  ],
  "timeline": [
    { "action": "appear",       "target": "service", "at": 0.0, "duration": 0.5 },
    { "action": "appear",       "target": "pod-1",   "at": 0.4, "duration": 0.5 },
    { "action": "connect",      "target": "e1",      "at": 0.9, "duration": 0.5 },
    { "action": "traffic",      "target": "e1",      "at": 1.4, "duration": 1.5 },
    { "action": "change_state", "target": "pod-1",   "at": 3.0, "duration": 0.5, "params": { "state": "unhealthy" } },
    { "action": "remove",       "target": "pod-1",   "at": 3.8, "duration": 0.5 }
  ]
}
```

The renderer interprets this into a GSAP timeline. **LLM flexibility + deterministic animation.**

## Architecture

```
frontend/ (React + TypeScript + Vite + GSAP + Zustand + Tailwind)
   │  REST + WebSocket
   ▼
backend/  (FastAPI + Python)
   ├── /api/transcribe   audio ─► text            (Whisper)
   ├── /api/generate     text  ─► Scene DSL        (LLM Gateway → validate/repair)
   ├── /api/assets       SVG asset manifest + markup
   └── /ws               real-time generation stream
```

### Key components

| Component | Location | Responsibility |
| --- | --- | --- |
| **LLM Gateway** | `backend/app/llm/` | Provider-agnostic (OpenAI / Ollama / offline mock). Text → Scene DSL. |
| **Scene models** | `backend/app/models/scene.py` | Pydantic schema for the DSL — the contract between AI and renderer. |
| **Validator / Critic** | `backend/app/scene/validator.py` | Repairs invalid edges/steps, remaps unknown asset types, reports warnings. |
| **Asset registry** | `backend/app/assets/registry.py` | Loads the SVG library, exposes available types to the LLM and the UI. |
| **STT** | `backend/app/stt/whisper_stt.py` | Whisper transcription (`faster-whisper`, with OpenAI API fallback). |
| **Animation engine** | `frontend/src/animation/engine.ts` | Compiles the DSL timeline into a GSAP timeline. |
| **Scene renderer** | `frontend/src/components/SceneCanvas.tsx` | Inline SVG rendering of objects/edges. |

## Quick start

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # optional: add an OpenAI key, else the offline mock is used
uvicorn app.main:app --reload --port 8000
```

The backend runs with **zero configuration** thanks to the offline mock LLM. Add `OPENAI_API_KEY` (or point at a local Ollama) for real generation.

Optional Whisper support (voice input):

```powershell
pip install -r requirements-whisper.txt
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the printed URL (default http://localhost:5173). The dev server proxies `/api` and `/ws` to the backend on port 8000.

## Configuration

All backend settings are environment variables (see [backend/.env.example](backend/.env.example)):

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_PROVIDER` | `auto` | `auto` \| `openai` \| `ollama` \| `mock` |
| `OPENAI_API_KEY` | — | Enables the OpenAI provider |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model for DSL generation |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder` | Ollama model |
| `WHISPER_MODEL` | `base` | faster-whisper model size |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |

## Roadmap

- [x] Voice → text → Scene DSL → animated SVG (MVP)
- [x] Offline mock generator (runs with no API keys)
- [x] Deterministic validator / critic pass
- [ ] RAG grounding on official docs (Kubernetes, Kafka, AWS …)
- [ ] Conversational scene editing ("make the failed pod red")
- [ ] Export to MP4 / WebM / GIF / Lottie
- [ ] GitHub / Confluence connectors for architecture explanations

## License

[MIT](LICENSE)
