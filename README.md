# Open LLM VTuber Avatar Lab

Overlay tooling for Open-LLM-VTuber v1.2.1 that adds:

- MediaPipe Holistic + Kalidokit motion capture for face, body, arms, and hands.
- Live2D parameter bridging for common face/body/arm/hand parameter IDs.
- OpenAI-backed avatar rig planning and voice sample generation.
- An avatar factory package generator with Live2D and Inochi2D parameter maps.

This repository is intentionally an overlay, not a vendored copy of Open-LLM-VTuber.

## Apply

From an Open-LLM-VTuber v1.2.1 checkout with the frontend source beside the release:

```bash
cp -R overlay/frontend-src/. /path/to/Open-LLM-VTuber-Web/
cp -R overlay/olv-release/. /path/to/Open-LLM-VTuber/
```

Then install the frontend dependencies:

```bash
cd /path/to/Open-LLM-VTuber-Web
npm install @mediapipe/tasks-vision@^0.10.35 kalidokit@^1.1.5
npm run build:web
cp -R dist/web/. /path/to/Open-LLM-VTuber/frontend/
```

Run the backend:

```bash
cd /path/to/Open-LLM-VTuber
uv run run_server.py
```

Open `http://localhost:12393/`, then enable `Settings -> Live2D -> Motion Capture`.

## Avatar Factory

```bash
cd /path/to/Open-LLM-VTuber
uv run python scripts/openai_avatar_assistant.py avatar-package \
  --image /path/to/avatar.png \
  --output-dir outputs/avatar-factory
```

With OpenAI vision:

```bash
OPENAI_API_KEY=... uv run python scripts/openai_avatar_assistant.py rig-plan \
  --image /path/to/avatar.png \
  --output outputs/rig-plan.json
```

The generated package contains source texture, rig plan, Live2D parameter map, Inochi2D parameter map, and an INP-layout draft container. It is not a finished rig; separated layers, meshes, deformers, and parameter keyforms still need authoring.

## OpenAI Voice

Use the included `characters/en_openai_voice.yaml` preset after setting:

```bash
export OPENAI_API_KEY=...
```

The preset switches `tts_model` to `openai_tts` and uses hosted OpenAI TTS through `https://api.openai.com/v1`.

## Sources

- Open-LLM-VTuber: https://github.com/Open-LLM-VTuber/Open-LLM-VTuber
- MediaPipe Tasks Vision: https://ai.google.dev/edge/mediapipe/solutions/vision/holistic_landmarker
- Kalidokit: https://github.com/yeemachine/kalidokit
- Inochi2D: https://github.com/Inochi2D/inochi2d
