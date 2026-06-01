# Open LLM VTuber Avatar Lab

This fork is a full source checkout, not an overlay. The server app lives at the repository root, and the rebuildable web frontend source lives in `frontend-src/`.

## Added Capabilities

- MediaPipe Holistic and Kalidokit motion capture for face, body, arms, and hands.
- Live2D parameter bridging for common face, body, arm, and hand parameter IDs.
- `scripts/openai_avatar_assistant.py` for OpenAI vision rig plans, PNG avatar packages, and OpenAI TTS samples.
- `characters/en_openai_voice.yaml` for hosted OpenAI TTS through the existing `openai_tts` engine.
- Inochi2D-style parameter maps and an INP-layout draft package path for open 2D puppet workflows.

## Run

```bash
uv run run_server.py
```

Open `http://localhost:12393/`, then enable `Settings -> Live2D -> Motion Capture`.

## Rebuild Frontend

```bash
cd frontend-src
npm install
npm run build:web
cp -R dist/web/. ../frontend/
```

## Avatar Factory

```bash
uv run python scripts/openai_avatar_assistant.py avatar-package \
  --image avatars/shizuku.png \
  --output-dir outputs/avatar-factory
```

With OpenAI vision:

```bash
OPENAI_API_KEY=... uv run python scripts/openai_avatar_assistant.py rig-plan \
  --image avatars/shizuku.png \
  --output outputs/rig-plan.json
```

The helper also accepts an `api_key` from `.codex/config.toml` or `~/.codex/config.toml` when `OPENAI_API_KEY` is not exported.

## OpenAI Voice

Use `characters/en_openai_voice.yaml` after setting:

```bash
export OPENAI_API_KEY=...
```

For a one-off voice sample:

```bash
uv run python scripts/openai_avatar_assistant.py voice \
  --text "Hello from the avatar lab." \
  --output outputs/openai-voice.mp3
```

## Large Local Models

The local `models/` directory from a release run is intentionally not committed because it can contain files larger than GitHub's normal file limit. Download or generate local ASR/TTS model assets using the upstream project instructions when needed.
