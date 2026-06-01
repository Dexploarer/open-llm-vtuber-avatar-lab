# Implementation Notes

## Motion Capture

`use-live2d-motion-capture.ts` creates one webcam stream and one MediaPipe Holistic tracker. Each frame is solved with Kalidokit:

- face landmarks -> head, eyes, pupils, mouth
- pose landmarks -> spine, upper arms, forearms
- hand landmarks -> wrists

The solved frame is passed into `LAppModel.setMotionCaptureFrame`. `LAppModel.update()` applies it during the normal Cubism update loop, after pointer drag and before breath/physics.

## Parameter Strategy

Live2D models vary. Standard face parameters are common, but arm and hand names are not universal. The bridge writes several common candidate IDs such as `ParamArmLX`, `ParamLeftArmX`, `ParamHandLX`, and `ParamLeftHandX`. Models without those parameters ignore them.

## Avatar Factory

`openai_avatar_assistant.py` has three commands:

- `rig-plan`: calls OpenAI vision and writes JSON guidance.
- `avatar-package`: creates a local package from a PNG without requiring OpenAI.
- `voice`: creates an OpenAI TTS sample.

The Inochi2D output is an INP-layout draft container based on the public INP container structure. It is meant as an open-format handoff artifact, not a finished model.
