"""Pre-download the ONNX model files so they are baked into the Docker image
instead of being fetched on the first user request.

Run during `docker build`:  python -m scripts.fetch_models
A network failure here is not fatal - the detector still lazy-downloads at runtime.
"""

import sys


def main() -> int:
    from app.emotion_model import detector as d

    steps = [
        ("YuNet face detector", d._get_yunet),
        ("HSEmotion emotion model", d._get_hse_net),
        ("FER+ fallback model", d._get_fer_net),
    ]
    failed = 0
    for label, loader in steps:
        try:
            loader()
            print(f"OK   {label}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"WARN {label}: {exc}", file=sys.stderr)
    if failed:
        print(f"{failed} model(s) not pre-fetched; they will download on first use.", file=sys.stderr)
    return 0  # never break the build


if __name__ == "__main__":
    raise SystemExit(main())
