# Wrist

Voice-controlled markdown editor for hands-free writing. Built with [LiveKit Agents](https://docs.livekit.io/agents/) and Claude.

## Setup

```bash
uv sync
```

Create a `.env.local` with your API keys:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

Start a local LiveKit server:

```bash
brew install livekit
livekit-server --dev
```

## Usage

**Voice console (push-to-talk):**

```bash
uv run python -m src.agent console
```

Press `Tab` to toggle the microphone on/off.

**Text console:**

```bash
uv run python -m src.agent --text
```

**As a LiveKit worker (connects to a remote LiveKit server):**

```bash
uv run python -m src.agent start
```

## Configuration

- `WRIST_WORKSPACE_DIR` — directory containing markdown files to edit (default: `~/markdown`)
- `--input-device <name>` — select a specific microphone in console mode
