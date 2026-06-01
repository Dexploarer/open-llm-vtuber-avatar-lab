import { useEffect } from 'react';
import {
  HolisticLandmarker,
  FilesetResolver,
  type Landmark,
  type NormalizedLandmark,
} from '@mediapipe/tasks-vision';
import {
  Face,
  Hand,
  Pose,
  type Side,
  type TFace,
  type THandUnsafe,
  type TPose,
} from 'kalidokit';
import { LAppLive2DManager } from '../../../WebSDK/src/lapplive2dmanager';
import { Live2DMotionCaptureFrame } from '../../../WebSDK/src/live2d-motion-capture';

const VISION_WASM_URL = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.35/wasm';
const HOLISTIC_LANDMARKER_MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/latest/holistic_landmarker.task';
const LEFT_SIDE: Side = 'Left';
const RIGHT_SIDE: Side = 'Right';

interface UseLive2DMotionCaptureProps {
  enabled: boolean;
}

const clamp = (value: number, min: number, max: number): number => Math.min(Math.max(value, min), max);

const buildFaceFrame = (face: TFace): Live2DMotionCaptureFrame => ({
  angleX: clamp(face.head.degrees.y, -30, 30),
  angleY: clamp(-face.head.degrees.x, -30, 30),
  angleZ: clamp(-face.head.degrees.z, -30, 30),
  bodyAngleX: clamp(face.head.degrees.y / 3, -10, 10),
  eyeBallX: clamp(face.pupil.x, -1, 1),
  eyeBallY: clamp(-face.pupil.y, -1, 1),
  eyeLOpen: clamp(face.eye.l, 0, 1),
  eyeROpen: clamp(face.eye.r, 0, 1),
  mouthOpenY: clamp(face.mouth.y, 0, 1),
  mouthForm: clamp(face.mouth.x, -1, 1),
});

const buildPoseFrame = (pose: TPose): Live2DMotionCaptureFrame => ({
  bodyAngleX: clamp(pose.Spine.y * 18, -10, 10),
  bodyAngleY: clamp(-pose.Spine.x * 18, -10, 10),
  bodyAngleZ: clamp(pose.Spine.z * 18, -10, 10),
  leftArmX: clamp(pose.LeftUpperArm.x * 18, -30, 30),
  leftArmY: clamp(pose.LeftUpperArm.y * 18, -30, 30),
  leftArmZ: clamp(pose.LeftUpperArm.z * 18, -30, 30),
  rightArmX: clamp(pose.RightUpperArm.x * 18, -30, 30),
  rightArmY: clamp(pose.RightUpperArm.y * 18, -30, 30),
  rightArmZ: clamp(pose.RightUpperArm.z * 18, -30, 30),
  leftForearmX: clamp(pose.LeftLowerArm.x * 18, -30, 30),
  leftForearmY: clamp(pose.LeftLowerArm.y * 18, -30, 30),
  rightForearmX: clamp(pose.RightLowerArm.x * 18, -30, 30),
  rightForearmY: clamp(pose.RightLowerArm.y * 18, -30, 30),
});

const buildHandFrame = (
  leftHand: THandUnsafe<'Left'> | undefined,
  rightHand: THandUnsafe<'Right'> | undefined,
): Live2DMotionCaptureFrame => ({
  leftHandX: leftHand ? clamp(leftHand.LeftWrist.y * 20, -30, 30) : undefined,
  leftHandY: leftHand ? clamp(leftHand.LeftWrist.x * 20, -30, 30) : undefined,
  rightHandX: rightHand ? clamp(rightHand.RightWrist.y * 20, -30, 30) : undefined,
  rightHandY: rightHand ? clamp(rightHand.RightWrist.x * 20, -30, 30) : undefined,
});

const applyFrame = (frame: Live2DMotionCaptureFrame | null): void => {
  const model = LAppLive2DManager.getInstance().getModel(0);
  model?.setMotionCaptureFrame(frame);
};

export const useLive2DMotionCapture = ({ enabled }: UseLive2DMotionCaptureProps): void => {
  useEffect(() => {
    if (!enabled) {
      applyFrame(null);
      return undefined;
    }

    let active = true;
    let animationFrame = 0;
    let stream: MediaStream | null = null;
    let holisticLandmarker: HolisticLandmarker | null = null;
    const video = document.createElement('video');
    video.autoplay = true;
    video.muted = true;
    video.playsInline = true;

    const stop = (): void => {
      active = false;
      if (animationFrame !== 0) {
        cancelAnimationFrame(animationFrame);
      }
      if (stream != null) {
        stream.getTracks().forEach((track) => track.stop());
      }
      applyFrame(null);
    };

    const run = async (): Promise<void> => {
      const vision = await FilesetResolver.forVisionTasks(VISION_WASM_URL);
      holisticLandmarker = await HolisticLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: HOLISTIC_LANDMARKER_MODEL_URL,
          delegate: 'GPU',
        },
        runningMode: 'VIDEO',
      });

      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: 640,
          height: 480,
          facingMode: 'user',
        },
        audio: false,
      });

      video.srcObject = stream;
      await video.play();

      const tick = (): void => {
        if (!active || holisticLandmarker == null) return;

        const result = holisticLandmarker.detectForVideo(video, performance.now());
        const frame: Live2DMotionCaptureFrame = {};
        const faceLandmarks: NormalizedLandmark[] | undefined = result.faceLandmarks[0];
        if (faceLandmarks) {
          const face = Face.solve(faceLandmarks, {
            runtime: 'mediapipe',
            video,
            smoothBlink: true,
          });
          if (face) {
            Object.assign(frame, buildFaceFrame(face));
          }
        }
        const poseLandmarks: NormalizedLandmark[] | undefined = result.poseLandmarks[0];
        const poseWorldLandmarks: Landmark[] | undefined = result.poseWorldLandmarks[0];
        if (poseLandmarks && poseWorldLandmarks) {
          const pose = Pose.solve(poseWorldLandmarks, poseLandmarks, {
            runtime: 'mediapipe',
            video,
            enableLegs: false,
          });
          if (pose) {
            Object.assign(frame, buildPoseFrame(pose));
          }
        }
        const leftHand = result.leftHandLandmarks[0]
          ? Hand.solve(result.leftHandLandmarks[0], LEFT_SIDE)
          : undefined;
        const rightHand = result.rightHandLandmarks[0]
          ? Hand.solve(result.rightHandLandmarks[0], RIGHT_SIDE)
          : undefined;
        Object.assign(frame, buildHandFrame(leftHand, rightHand));
        applyFrame(Object.keys(frame).length > 0 ? frame : null);

        animationFrame = requestAnimationFrame(tick);
      };

      tick();
    };

    run().catch((error: Error) => {
      console.error('[MotionCapture] Failed to start face tracking', error);
      stop();
    });

    return stop;
  }, [enabled]);
};
