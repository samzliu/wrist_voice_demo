# Wrist

Voice-AI workspace for hands-free writing, editing, and research. Built with [LiveKit Agents](https://docs.livekit.io/agents/) and Claude.

## Features

- **Voice-controlled editing** — talk to your AI coworker, see edits live in a TipTap editor
- **Multi-file workspace** — create, read, edit, delete, rename, and search across files
- **HTML slide decks** — create and present slides (960x540, inline CSS) with voice commands
- **Web search** — Exa-powered search and deep research with results displayed in-app
- **Website visiting** — fetch and read any URL, with Page/Text toggle for blocked iframes
- **Background deep thinking** — agent can research asynchronously while you keep talking
- **Reasoning trace** — Activity panel streams tool calls and agent thinking in real-time
- **Persona/script system** — load custom agent personas from markdown files
- **Pause/resume** — pause the agent without disconnecting
- **Turn-taking indicator** — see who's speaking, if the agent is thinking, or waiting for you
- **Custom turn detection** — continuous interpolation across three EMAs with Deepgram Flux end-of-turn confidence

## Setup

```bash
uv sync
cd web && npm install
```

Create `.env.local` in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
DEEPGRAM_API_KEY=...
EXA_API_KEY=...
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
WRIST_WORKSPACE_DIR=./editing
```

Create `web/.env.local`:

```
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
NEXT_PUBLIC_LIVEKIT_URL=ws://localhost:7880
WRIST_WORKSPACE_DIR=/absolute/path/to/workspace
```

Start a local LiveKit server:

```bash
brew install livekit
livekit-server --dev
```

## Usage

**Web UI (recommended):**

Start two terminals:

```bash
# Terminal 1 — agent
uv run python -m src.agent dev

# Terminal 2 — web
cd web && npm run dev
```

Open http://localhost:3000, pick a persona and workspace, click Connect.

**Voice console (push-to-talk):**

```bash
uv run python -m src.agent console
```

Press `Tab` to toggle the microphone.

**Text console:**

```bash
uv run python -m src.agent --text
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `WRIST_WORKSPACE_DIR` | Default workspace directory | `~/markdown` |
| `WRIST_SCRIPTS_DIR` | Directory of persona `.md` files | (none) |
| `WRIST_WORKSPACES_ROOT` | Parent directory listing workspace folders | (none) |
| `EXA_API_KEY` | Exa search API key | (none) |
| `ANTHROPIC_API_KEY` | Anthropic API key (agent LLM + deep thinking) | required |
| `DEEPGRAM_API_KEY` | Deepgram API key (speech-to-text) | required |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Web Client (Next.js 15 + React 19)                     │
│  ┌──────────┬──────────────────────┬──────────────────┐ │
│  │ File     │ Main Content         │ Activity Panel   │ │
│  │ Sidebar  │ Editor / Slides /    │ Tool calls +     │ │
│  │          │ Search / Web         │ reasoning trace  │ │
│  ├──────────┴──────────────────────┴──────────────────┤ │
│  │ Bottom Bar (mic · pause · monologue · turn status) │ │
│  └────────────────────────────────────────────────────┘ │
│                  ↕ LiveKit Data Channel                  │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Voice Agent (Python)                               │ │
│  │  STT: Deepgram Flux  ·  LLM: Claude Haiku 4.5     │ │
│  │  TTS: ElevenLabs Flash v2.5  ·  VAD: Silero       │ │
│  │                                                    │ │
│  │  Tools:                                            │ │
│  │  · Markdown editing (read/write/search/sections)   │ │
│  │  · File CRUD (create/read/write/delete/rename)     │ │
│  │  · HTML slides (create/edit/delete/present)        │ │
│  │  · Web search (Exa) + deep research                │ │
│  │  · Website visiting (fetch + text extraction)      │ │
│  │  · Workspace grep/search                           │ │
│  │  · Deep thinking (sync + async background)         │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Deep Thinking

Two modes:
- **`deep_think`** — blocks the conversation, returns result directly
- **`deep_think_background`** — runs in background via `DeepAgentBridge`, streams progress to Activity panel, and injects results back into the voice conversation via `session.generate_reply()` when complete

### Data Channel Protocol

All client-agent communication uses LiveKit data channels with typed JSON messages. See `web/lib/protocol.ts` for the full type definitions.

### Turn Detection

Custom continuous interpolation system using three exponential moving averages (utterance pause, response latency, turn pause) combined with Deepgram Flux end-of-turn confidence. See `docs/turn-taking.md` for details.
