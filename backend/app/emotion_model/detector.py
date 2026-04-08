import base64
import importlib.util
import logging
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

EMOTION_MAP = {
    "happy": "happiness",
    "sad": "sadness",
    "angry": "anger",
    "fear": "fear",
    "disgust": "anger",
    "surprise": "neutrality",
    "neutral": "neutrality",
}

EMOTION_DESCRIPTIONS = {
    "happiness": "You seem relaxed and positive.",
    "sadness": "You may be feeling low; a gentle break can help.",
    "anger": "You seem tense; consider slow breathing for a minute.",
    "fear": "You may be fearful right now; grounding can reduce stress.",
    "anxiety": "You look anxious; take a moment to settle your thoughts.",
    "stress": "You appear stressed, try uncluttering your mind.",
    "neutrality": "You appear calm and steady.",
}

# FER+ ONNX class order (onnx/models zoo)
_FERPLUS_LABELS = ("neutral", "happiness", "surprise", "sadness", "anger", "disgust", "fear", "contempt")

# Map FER+ labels to DeepFace-style keys used by EMOTION_MAP
_FER_TO_DOM = {
    "neutral": "neutral",
    "happiness": "happy",
    "surprise": "surprise",
    "sadness": "sad",
    "anger": "angry",
    "disgust": "disgust",
    "fear": "fear",
    "contempt": "neutral",
}

# Git LFS files must use media.githubusercontent.com, not raw.githubusercontent.com
_ONNX_URL = (
    "https://media.githubusercontent.com/media/onnx/models/main/"
    "validated/vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
)
_WEIGHTS_DIR = Path(__file__).resolve().parent / "weights"
_ONNX_PATH = _WEIGHTS_DIR / "emotion-ferplus-8.onnx"
_MIN_ONNX_BYTES = 1_000_000

_init_lock = threading.Lock()
_fer_net = None
_face_cascade = None


def decode_image_sync(b64: str) -> np.ndarray:
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    img_bytes = base64.b64decode(b64)
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Decoded image is None")
    return img


async def decode_image(image_base64: str | None, image_file: UploadFile | None) -> str:
    original_b64 = None
    if image_base64:
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]
        original_b64 = image_base64
    elif image_file:
        content = await image_file.read()
        original_b64 = base64.b64encode(content).decode("utf-8")
    if not original_b64:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide image_base64 or image_file")
    return original_b64


def _softmax(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float64).reshape(-1)
    x = x - np.max(x)
    e = np.exp(x)
    return (e / np.sum(e)).astype(np.float64)


def _ensure_onnx_model() -> Path:
    _WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    if _ONNX_PATH.is_file() and _ONNX_PATH.stat().st_size >= _MIN_ONNX_BYTES:
        return _ONNX_PATH
    with _init_lock:
        if _ONNX_PATH.is_file() and _ONNX_PATH.stat().st_size >= _MIN_ONNX_BYTES:
            return _ONNX_PATH
        tmp = _ONNX_PATH.with_suffix(".onnx.part")
        logger.info("Downloading emotion model (~35 MB) to %s", _ONNX_PATH)
        try:
            with urllib.request.urlopen(_ONNX_URL, timeout=300) as resp, open(tmp, "wb") as out:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
        except (urllib.error.URLError, OSError) as exc:
            if tmp.is_file():
                tmp.unlink(missing_ok=True)
            logger.exception("Failed to download FER+ ONNX model")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not download face emotion model: {exc}",
            ) from exc
        tmp.replace(_ONNX_PATH)
    return _ONNX_PATH


def _get_face_cascade() -> cv2.CascadeClassifier:
    global _face_cascade
    if _face_cascade is None:
        with _init_lock:
            if _face_cascade is None:
                path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                _face_cascade = cv2.CascadeClassifier(path)
                if _face_cascade.empty():
                    raise RuntimeError("OpenCV Haar cascade for face detection failed to load")
    return _face_cascade


def _get_fer_net() -> cv2.dnn.Net:
    global _fer_net
    if _fer_net is None:
        with _init_lock:
            if _fer_net is None:
                onnx = _ensure_onnx_model()
                _fer_net = cv2.dnn.readNetFromONNX(str(onnx))
    return _fer_net


def _largest_face_roi(gray: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    cascade = _get_face_cascade()
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
    if faces is None or len(faces) == 0:
        return None
    return max(faces, key=lambda f: int(f[2]) * int(f[3]))


def _analyze_opencv_ferplus(img: np.ndarray) -> Tuple[str, float, str]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face = _largest_face_roi(gray)
    if face is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No face detected in the image.")

    x, y, w, h = (int(v) for v in face)
    h_img, w_img = gray.shape[:2]
    pad = max(8, int(0.12 * max(w, h)))
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(w_img, x + w + pad), min(h_img, y + h + pad)
    roi = gray[y0:y1, x0:x1]
    if roi.size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No face detected in the image.")

    # FER+ expects Nx1x64x64; blobFromImage builds NCHW from 1-channel Mat
    blob = cv2.dnn.blobFromImage(roi, scalefactor=1.0 / 255.0, size=(64, 64), mean=(0, 0, 0), swapRB=False)
    net = _get_fer_net()
    net.setInput(blob)
    out = net.forward()
    scores = np.array(out).reshape(-1)
    probs = _softmax(scores)
    idx = int(np.argmax(probs))
    confidence = round(float(probs[idx]), 3)
    fer_label = _FERPLUS_LABELS[idx]
    dom = _FER_TO_DOM[fer_label]
    mapped = EMOTION_MAP.get(dom, "neutrality")
    desc = EMOTION_DESCRIPTIONS.get(mapped, "Thanks for sharing how you feel.")
    return mapped, confidence, desc


def _analyze_deepface(img: np.ndarray) -> Tuple[str, float, str]:
    from deepface import DeepFace

    try:
        res = DeepFace.analyze(
            img,
            actions=["emotion"],
            enforce_detection=True,
            detector_backend="retinaface",
            silent=True,
        )
        if isinstance(res, list):
            res = res[0]
    except ValueError as ve:
        if "Face could not be detected" in str(ve):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No face detected in the image.") from ve
        raise

    dom = res.get("dominant_emotion", "neutral")
    emotion_weights = res.get("emotion", {})
    raw_confidence = emotion_weights.get(dom, 50.0)
    confidence = round(max(0.0, min(1.0, float(raw_confidence) / 100.0)), 3)
    mapped = EMOTION_MAP.get(dom, "neutrality")
    desc = EMOTION_DESCRIPTIONS.get(mapped, "Thanks for sharing how you feel.")
    return mapped, confidence, desc


def analyze_emotion(base64_img: str) -> Tuple[str, float, str]:
    try:
        img = decode_image_sync(base64_img)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unreadable image",
        ) from exc

    try:
        if importlib.util.find_spec("deepface") is not None:
            try:
                return _analyze_deepface(img)
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning("DeepFace failed, using OpenCV FER+ fallback: %s", exc)
        return _analyze_opencv_ferplus(img)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Emotion analysis failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image analysis failed: {exc}",
        ) from exc
