import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import struct
from pathlib import Path

from openai import OpenAI


def image_data_url(path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        raise ValueError(f"Unsupported image type: {path}")
    return f"data:{mime_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def codex_config_paths() -> list[Path]:
    return [Path.cwd() / ".codex" / "config.toml", Path.home() / ".codex" / "config.toml"]


def openai_key_from_codex_config() -> str | None:
    api_key_pattern = re.compile(r'^\s*api_key\s*=\s*["\']([^"\']+)["\']\s*$')
    for path in codex_config_paths():
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            match = api_key_pattern.match(line)
            if match and match.group(1).strip():
                return match.group(1).strip()
    return None


def require_openai_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY") or openai_key_from_codex_config()
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY or configure api_key in Codex config before using OpenAI avatar tooling.")
    return api_key


def default_parameter_bindings() -> list[dict[str, object]]:
    return [
        {"source": "face.head.yaw", "live2d": "ParamAngleX", "inochi2d": "Face::Yaw", "range": [-30, 30]},
        {"source": "face.head.pitch", "live2d": "ParamAngleY", "inochi2d": "Face::Pitch", "range": [-30, 30]},
        {"source": "face.head.roll", "live2d": "ParamAngleZ", "inochi2d": "Face::Roll", "range": [-30, 30]},
        {"source": "face.eye.left", "live2d": "ParamEyeLOpen", "inochi2d": "Eye::LeftOpen", "range": [0, 1]},
        {"source": "face.eye.right", "live2d": "ParamEyeROpen", "inochi2d": "Eye::RightOpen", "range": [0, 1]},
        {"source": "face.pupil.x", "live2d": "ParamEyeBallX", "inochi2d": "Eye::LookX", "range": [-1, 1]},
        {"source": "face.pupil.y", "live2d": "ParamEyeBallY", "inochi2d": "Eye::LookY", "range": [-1, 1]},
        {"source": "face.mouth.open", "live2d": "ParamMouthOpenY", "inochi2d": "Mouth::Open", "range": [0, 1]},
        {"source": "face.mouth.form", "live2d": "ParamMouthForm", "inochi2d": "Mouth::Form", "range": [-1, 1]},
        {"source": "pose.spine.x", "live2d": "ParamBodyAngleX", "inochi2d": "Body::Yaw", "range": [-10, 10]},
        {"source": "pose.spine.y", "live2d": "ParamBodyAngleY", "inochi2d": "Body::Pitch", "range": [-10, 10]},
        {"source": "pose.spine.z", "live2d": "ParamBodyAngleZ", "inochi2d": "Body::Roll", "range": [-10, 10]},
        {"source": "pose.leftUpperArm", "live2d": "ParamArmLX", "inochi2d": "Arm::LeftUpper", "range": [-30, 30]},
        {"source": "pose.rightUpperArm", "live2d": "ParamArmRX", "inochi2d": "Arm::RightUpper", "range": [-30, 30]},
        {"source": "hand.leftWrist", "live2d": "ParamHandLX", "inochi2d": "Hand::LeftWrist", "range": [-30, 30]},
        {"source": "hand.rightWrist", "live2d": "ParamHandRX", "inochi2d": "Hand::RightWrist", "range": [-30, 30]},
    ]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def pack_inochi_draft(path: Path, payload: dict[str, object], texture_path: Path) -> None:
    json_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    texture_payload = texture_path.read_bytes()
    with path.open("wb") as file:
        file.write(b"TRNSRTS\0")
        file.write(struct.pack(">I", len(json_payload)))
        file.write(json_payload)
        file.write(b"TEX_SECT")
        file.write(struct.pack(">I", 1))
        file.write(struct.pack(">I", len(texture_payload)))
        file.write(b"\x00")
        file.write(texture_payload)


def rig_plan(args: argparse.Namespace) -> None:
    image_path = Path(args.image).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    client = OpenAI(api_key=require_openai_key())
    response = client.chat.completions.create(
        model=args.model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Return only JSON. Build a Live2D-style rigging plan for a user-owned 2D avatar image. "
                    "Do not claim to generate proprietary .moc3 files. Include suggested layer cuts, "
                    "mesh regions, deformers, parameter mappings, and motion-capture bindings."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this character image for a legal auto-rigging workflow. "
                            "Use parameter names like ParamAngleX, ParamAngleY, ParamAngleZ, "
                            "ParamEyeLOpen, ParamEyeROpen, ParamMouthOpenY, ParamMouthForm, "
                            "ParamEyeBallX, and ParamEyeBallY."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": image_data_url(image_path)}},
                ],
            },
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty rigging plan.")
    parsed: dict[str, object] = json.loads(content)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    print(output_path)


def avatar_package(args: argparse.Namespace) -> None:
    image_path = Path(args.image).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    texture_dir = output_dir / "textures"
    plans_dir = output_dir / "plans"
    texture_dir.mkdir(parents=True, exist_ok=True)
    source_texture = texture_dir / image_path.name
    shutil.copyfile(image_path, source_texture)

    if args.rig_plan:
        rig_payload = json.loads(Path(args.rig_plan).expanduser().resolve().read_text(encoding="utf-8"))
    else:
        rig_payload = {
            "status": "draft",
            "source_image": image_path.name,
            "layer_cut_order": [
                "head",
                "hair_front",
                "hair_back",
                "eyes",
                "mouth",
                "neck",
                "torso",
                "left_arm",
                "right_arm",
                "left_hand",
                "right_hand",
            ],
            "parameters": default_parameter_bindings(),
        }

    bindings = default_parameter_bindings()
    live2d_map = {
        "format": "live2d-parameter-map",
        "source_texture": f"textures/{source_texture.name}",
        "bindings": [{"source": item["source"], "parameter": item["live2d"], "range": item["range"]} for item in bindings],
    }
    inochi_map = {
        "format": "inochi2d-parameter-map",
        "source_texture": f"textures/{source_texture.name}",
        "bindings": [{"source": item["source"], "parameter": item["inochi2d"], "range": item["range"]} for item in bindings],
    }
    inochi_payload = {
        "format": "inochi2d-draft",
        "generator": "openai_avatar_assistant.py",
        "source_texture": source_texture.name,
        "rig_plan": rig_payload,
        "parameters": inochi_map["bindings"],
        "notes": [
            "This is an INP-container draft for open-source Inochi2D tooling.",
            "Use Inochi Creator to replace the draft metadata with authored meshes and deformers.",
        ],
    }
    readme = "\n".join(
        [
            "# Avatar Factory Package",
            "",
            "This package starts from a flat PNG and prepares the artifacts needed for real 2D rigging.",
            "",
            "- `textures/` contains the source art.",
            "- `plans/rig-plan.json` describes suggested layer cuts, meshes, deformers, and mocap bindings.",
            "- `plans/live2d-parameter-map.json` maps mocap sources to Live2D-style params.",
            "- `plans/inochi2d-parameter-map.json` maps the same sources to open Inochi2D-style params.",
            "- `avatar-factory-draft.inp` is an INP-layout draft container, not a finished rig.",
            "",
            "A finished puppet still needs separated layers, meshes, deformers, and authored parameter keyforms.",
        ]
    )

    write_json(plans_dir / "rig-plan.json", rig_payload)
    write_json(plans_dir / "live2d-parameter-map.json", live2d_map)
    write_json(plans_dir / "inochi2d-parameter-map.json", inochi_map)
    write_json(plans_dir / "inochi2d-draft.json", inochi_payload)
    (output_dir / "README.md").write_text(readme + "\n", encoding="utf-8")
    pack_inochi_draft(output_dir / "avatar-factory-draft.inp", inochi_payload, source_texture)
    print(output_dir)


def voice(args: argparse.Namespace) -> None:
    output_path = Path(args.output).expanduser().resolve()
    client = OpenAI(api_key=require_openai_key())
    response = client.audio.speech.create(
        model=args.model,
        voice=args.voice,
        input=args.text,
        response_format=args.format,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response.stream_to_file(output_path)
    print(output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenAI helpers for avatar rig planning and voice samples.")
    subparsers = parser.add_subparsers(required=True)

    rig_parser = subparsers.add_parser("rig-plan")
    rig_parser.add_argument("--image", required=True)
    rig_parser.add_argument("--output", default="outputs/rig-plan.json")
    rig_parser.add_argument("--model", default="gpt-4o-mini")
    rig_parser.set_defaults(func=rig_plan)

    package_parser = subparsers.add_parser("avatar-package")
    package_parser.add_argument("--image", required=True)
    package_parser.add_argument("--rig-plan")
    package_parser.add_argument("--output-dir", default="outputs/avatar-factory")
    package_parser.set_defaults(func=avatar_package)

    voice_parser = subparsers.add_parser("voice")
    voice_parser.add_argument("--text", required=True)
    voice_parser.add_argument("--output", default="outputs/openai-voice.mp3")
    voice_parser.add_argument("--model", default="tts-1")
    voice_parser.add_argument("--voice", default="nova")
    voice_parser.add_argument("--format", default="mp3")
    voice_parser.set_defaults(func=voice)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
