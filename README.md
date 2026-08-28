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

The backend runs with **zero configuration** thanks to the offline mock generator — but for real AI you have two easy options:

**Recommended: fully local AI, no API keys** — using [Ollama](https://ollama.com):

```powershell
ollama serve                       # start the local model server
ollama pull qwen2.5-coder:1.5b     # small + fast (~8s/scene); use :7b for higher quality
```

Then in `backend/.env` set `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=qwen2.5-coder:1.5b`.

**Or OpenAI** — put a valid `OPENAI_API_KEY` in `backend/.env` and set `LLM_PROVIDER=openai` (or `auto`).

**Voice input (local Whisper)** — transcribes speech on the backend, no keys:

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

> Tip: on Windows you can run [scripts/dev-backend.ps1](scripts/dev-backend.ps1) and
> [scripts/dev-frontend.ps1](scripts/dev-frontend.ps1) to set up and start each side in one step.

## Configuration

All backend settings are environment variables (see [backend/.env.example](backend/.env.example)):

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_PROVIDER` | `auto` | `auto` \| `openai` \| `ollama` \| `mock` |
| `OPENAI_API_KEY` | — | Enables the OpenAI provider |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model for DSL generation |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder:1.5b` | Ollama model (`:1.5b` fast, `:7b` higher quality) |
| `WHISPER_MODEL` | `base` | faster-whisper model size |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins |

## Testing

Backend unit + API tests run fully offline (they force the mock provider, no keys or network):

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Frontend type-check:

```powershell
cd frontend
npm run typecheck
```

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
