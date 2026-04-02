# Wrist

Voice-AI workspace for hands-free writing, editing, and research. Built with [LiveKit Agents](https://docs.livekit.io/agents/) and Claude.

## Features

- **Voice-controlled editing** — talk to your AI coworker, see edits live
- **Multi-file workspace** — create, read, edit, delete, and search across files
- **HTML slide decks** — create and present slides with voice commands
- **Web search** — Exa-powered search and deep research, results displayed in-app
- **Website visiting** — fetch and read any URL
- **Background deep thinking** — agent can research in the background while you keep talking
- **Reasoning trace** — see tool calls and agent thinking in real-time in the Activity panel
- **Persona/script system** — load custom personas from markdown files
- **Pause/resume** — pause the agent without disconnecting

## Setup

```bash
uv sync
```

Create a `.env.local` with your API keys:

```
ANTHROPIC_API_KEY=sk-ant-...
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
EXA_API_KEY=...
```

Start a local LiveKit server:

```bash
brew install livekit
livekit-server --dev
```

### Web UI

```bash
cd web
npm install
npm run dev
```

Then open http://localhost:3000. Select a persona and workspace, then connect.

## Usage

**Web UI (recommended):**

1. Start the agent: `uv run python -m src.agent start`
2. Start the web app: `cd web && npm run dev`
3. Open http://localhost:3000, configure, and connect

**Voice console (push-to-talk):**

```bash
uv run python -m src.agent console
```

Press `Tab` to toggle the microphone on/off.

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
| `ANTHROPIC_API_KEY` | Anthropic API key for deep thinking | (required) |
| `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | LiveKit connection | (required) |

## Architecture

```
┌──────────────────────────────────────────────────┐
│  Web Client (Next.js)                            │
│  ┌──────────┬─────────────────┬────────────────┐ │
│  │ File     │ Main Content    │ Reasoning      │ │
│  │ Sidebar  │ (Editor/Slides/ │ Panel          │ │
│  │          │  Search/Web)    │ (Activity log) │ │
│  ├──────────┴─────────────────┴────────────────┤ │
│  │ Bottom Control Bar (mic/pause/monologue)    │ │
│  └─────────────────────────────────────────────┘ │
│              ↕ LiveKit Data Channel               │
│  ┌─────────────────────────────────────────────┐ │
│  │ Voice Agent (Python)                        │ │
│  │  ├─ File CRUD tools                         │ │
│  │  ├─ Markdown editing tools                  │ │
│  │  ├─ HTML slide tools                        │ │
│  │  ├─ Exa search / web fetch tools            │ │
│  │  ├─ Workspace grep/search                   │ │
│  │  └─ Deep thinking (sync + async background) │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Data Channel Protocol

All communication between the web client and voice agent uses LiveKit's data channel with JSON messages. See `web/lib/protocol.ts` for the full type definitions.

### Deep Thinking

Two modes:
- **`deep_think`** — blocks the conversation, returns result directly
- **`deep_think_background`** — runs in background, agent continues talking. Uses `DeepAgentBridge` to stream progress to the Activity panel and `session.generate_reply()` to seamlessly inject results back into the voice conversation when complete.
