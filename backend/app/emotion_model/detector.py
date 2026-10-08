import base64
import importlib.util
import logging
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

# App-facing emotion vocabulary (must stay within these keys — the frontend/DB expect them).
EMOTION_DESCRIPTIONS = {
    "happiness": "You seem relaxed and positive.",
    "sadness": "You may be feeling low; a gentle break can help.",
    "anger": "You seem tense; consider slow breathing for a minute.",
    "fear": "You may be fearful right now; grounding can reduce stress.",
    "anxiety": "You look anxious; take a moment to settle your thoughts.",
    "stress": "You appear stressed, try uncluttering your mind.",
    "neutrality": "You appear calm and steady.",
}

# DeepFace / FER+ style keys -> app vocabulary.
EMOTION_MAP = {
    "happy": "happiness",
    "sad": "sadness",
    "angry": "anger",
    "fear": "fear",
    "disgust": "anger",
    "surprise": "neutrality",
    "neutral": "neutrality",
    "contempt": "anger",
}

# ---- HSEmotion (AffectNet, EfficientNet-B0) — primary classifier -------------
# 8-class AffectNet order used by av-savchenko/face-emotion-recognition.
_HSE_LABELS = ("anger", "contempt", "disgust", "fear", "happiness", "neutral", "sadness", "surprise")
_HSE_TO_APP = {
    "anger": "anger",
    "contempt": "anger",
    "disgust": "anger",
    "fear": "fear",
    "happiness": "happiness",
    "neutral": "neutrality",
    "sadness": "sadness",
    "surprise": "neutrality",  # app vocabulary has no "surprise"
}
_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# ---- FER+ (ONNX model zoo) — fallback classifier ---------------------------
_FERPLUS_LABELS = ("neutral", "happiness", "surprise", "sadness", "anger", "disgust", "fear", "contempt")

_WEIGHTS_DIR = Path(__file__).resolve().parent / "weights"
_HSE_PATH = _WEIGHTS_DIR / "enet_b0_8_best_afew.onnx"
_FER_PATH = _WEIGHTS_DIR / "emotion-ferplus-8.onnx"
_YUNET_PATH = _WEIGHTS_DIR / "face_detection_yunet_2023mar.onnx"

_HSE_URL = (
    "https://raw.githubusercontent.com/av-savchenko/face-emotion-recognition/main/"
    "models/affectnet_emotions/onnx/enet_b0_8_best_afew.onnx"
)
# Git LFS assets must use media.githubusercontent.com, not raw.githubusercontent.com.
_FER_URL = (
    "https://media.githubusercontent.com/media/onnx/models/main/"
    "validated/vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
)
_YUNET_URL = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
    "models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
_MIN_HSE_BYTES = 5_000_000
_MIN_FER_BYTES = 1_000_000
_MIN_YUNET_BYTES = 50_000

_YUNET_SCORE_THRESHOLD = 0.6
_YUNET_NMS_THRESHOLD = 0.3
_MAX_ANALYSIS_DIM = 1280
_FACE_PAD_FRAC = 0.25

# RLock, not Lock: _get_hse_net/_get_fer_net/_get_yunet each acquire this, then call
# _ensure_model which acquires it again on the same thread when the model file is
# missing - a plain Lock would deadlock there forever (reproduced: the process just
# blocks on the second acquire, no timeout, no error). This only ever showed up on a
# cold cache, which is why it stayed hidden locally once the weights existed on disk.
_init_lock = threading.RLock()
_hse_net = None
_fer_net = None
_yunet = None
_face_cascades: Optional[List[cv2.CascadeClassifier]] = None


# --------------------------------------------------------------------------- I/O


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


def _downscale(img: np.ndarray, max_dim: int = _MAX_ANALYSIS_DIM) -> np.ndarray:
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest <= max_dim:
        return img
    scale = max_dim / float(longest)
    return cv2.resize(img, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_AREA)


def _clahe(gray: np.ndarray) -> np.ndarray:
    """Contrast-limited adaptive histogram equalisation — used only to aid face detection."""
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)


# ------------------------------------------------------------------------ models


def _ensure_model(path: Path, url: str, min_bytes: int, label: str) -> Path:
    _WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size >= min_bytes:
        return path
    with _init_lock:
        if path.is_file() and path.stat().st_size >= min_bytes:
            return path
        tmp = path.with_suffix(path.suffix + ".part")
        logger.info("Downloading %s model to %s", label, path)
        try:
            with urllib.request.urlopen(url, timeout=120) as resp, open(tmp, "wb") as out:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
        except (urllib.error.URLError, OSError) as exc:
            if tmp.is_file():
                tmp.unlink(missing_ok=True)
            logger.exception("Failed to download %s model", label)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not download face model: {exc}",
            ) from exc
        tmp.replace(path)
    return path


def _get_hse_net() -> Optional[cv2.dnn.Net]:
    """Primary emotion model (AffectNet EfficientNet-B0). None if it can't be loaded."""
    global _hse_net
    if _hse_net is None:
        with _init_lock:
            if _hse_net is None:
                try:
                    path = _ensure_model(_HSE_PATH, _HSE_URL, _MIN_HSE_BYTES, "emotion (HSEmotion)")
                    _hse_net = cv2.dnn.readNetFromONNX(str(path))
                except Exception as exc:  # noqa: BLE001 - fall back to FER+ on any failure
                    logger.warning("HSEmotion model unavailable, will use FER+ fallback: %s", exc)
                    return None
    return _hse_net


def _get_fer_net() -> cv2.dnn.Net:
    global _fer_net
    if _fer_net is None:
        with _init_lock:
            if _fer_net is None:
                onnx = _ensure_model(_FER_PATH, _FER_URL, _MIN_FER_BYTES, "emotion (FER+)")
                _fer_net = cv2.dnn.readNetFromONNX(str(onnx))
    return _fer_net


def _get_yunet() -> Optional["cv2.FaceDetectorYN"]:
    global _yunet
    if _yunet is None:
        if not hasattr(cv2, "FaceDetectorYN"):
            return None
        with _init_lock:
            if _yunet is None:
                try:
                    path = _ensure_model(_YUNET_PATH, _YUNET_URL, _MIN_YUNET_BYTES, "face detector (YuNet)")
                    _yunet = cv2.FaceDetectorYN.create(
                        str(path), "", (320, 320), _YUNET_SCORE_THRESHOLD, _YUNET_NMS_THRESHOLD, 5000
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("YuNet unavailable, using Haar cascades: %s", exc)
                    return None
    return _yunet


def _get_face_cascades() -> List[cv2.CascadeClassifier]:
    global _face_cascades
    if _face_cascades is None:
        with _init_lock:
            if _face_cascades is None:
                names = [
                    "haarcascade_frontalface_default.xml",
                    "haarcascade_frontalface_alt2.xml",
                    "haarcascade_profileface.xml",
                ]
                loaded = [cv2.CascadeClassifier(cv2.data.haarcascades + n) for n in names]
                loaded = [c for c in loaded if not c.empty()]
                if not loaded:
                    raise RuntimeError("No OpenCV Haar face cascade could be loaded")
                _face_cascades = loaded
    return _face_cascades


# ---------------------------------------------------------------- face detection

# (x, y, w, h) box in pixels.
Box = Tuple[int, int, int, int]


def _detect_with_yunet(bgr: np.ndarray) -> Optional[List[Box]]:
    det = _get_yunet()
    if det is None:
        return None
    h, w = bgr.shape[:2]
    det.setInputSize((w, h))
    try:
        _, faces = det.detect(bgr)
    except cv2.error:
        return None
    out: List[Box] = []
    if faces is not None:
        for f in faces:
            x, y, fw, fh = (int(round(v)) for v in f[:4])
            if fw > 0 and fh > 0:
                out.append((max(0, x), max(0, y), fw, fh))
    return out


def _iou(a: Box, b: Box) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


def _detect_with_haar(gray: np.ndarray) -> List[Box]:
    h, w = gray.shape[:2]
    min_side = max(48, int(0.12 * min(h, w)))
    seen: List[Box] = []
    for cascade in _get_face_cascades():
        rects = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(min_side, min_side))
        for (x, y, fw, fh) in rects:
            box = (int(x), int(y), int(fw), int(fh))
            if not any(_iou(box, s) > 0.4 for s in seen):
                seen.append(box)
        if seen:
            break
    return seen


def _detect_faces(bgr: np.ndarray) -> List[Box]:
    yunet = _detect_with_yunet(bgr)
    if yunet:
        return yunet
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    haar = _detect_with_haar(gray)
    if haar:
        return haar
    # Last resort: brighten + upscale, then retry.
    up = cv2.resize(_clahe(gray), None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    up_bgr = cv2.cvtColor(up, cv2.COLOR_GRAY2BGR)
    boosted = _detect_with_yunet(up_bgr) or _detect_with_haar(up)
    return [(int(x / 1.5), int(y / 1.5), int(w / 1.5), int(h / 1.5)) for (x, y, w, h) in (boosted or [])]


def _crop_face(img: np.ndarray, box: Box, pad_frac: float = _FACE_PAD_FRAC) -> np.ndarray:
    x, y, w, h = box
    H, W = img.shape[:2]
    pad = int(pad_frac * max(w, h))
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
    return img[y0:y1, x0:x1]


# ------------------------------------------------------------------- inference


def _hse_probs(bgr_face: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(cv2.resize(bgr_face, (224, 224), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    x = rgb.astype(np.float32) / 255.0
    x = (x - _IMAGENET_MEAN) / _IMAGENET_STD
    x = np.transpose(x, (2, 0, 1))[None]  # NCHW
    net = _get_hse_net()
    net.setInput(x)
    return _softmax(net.forward().reshape(-1))


def _analyze_hsemotion(img: np.ndarray, box: Box) -> Tuple[str, float, str]:
    face = _crop_face(img, box)
    # Light TTA: average upright + horizontal flip for a steadier read.
    probs = (_hse_probs(face) + _hse_probs(cv2.flip(face, 1))) / 2.0
    idx = int(np.argmax(probs))
    label = _HSE_LABELS[idx]
    mapped = _HSE_TO_APP.get(label, "neutrality")
    desc = EMOTION_DESCRIPTIONS.get(mapped, "Thanks for sharing how you feel.")
    return mapped, round(float(probs[idx]), 3), desc


def _analyze_ferplus(img: np.ndarray, box: Box) -> Tuple[str, float, str]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    roi = _crop_face(gray, box, pad_frac=0.15)
    roi64 = cv2.resize(roi, (64, 64), interpolation=cv2.INTER_AREA)  # plain grayscale, 0-255
    blob = cv2.dnn.blobFromImage(roi64.astype(np.float32), 1.0, (64, 64), (0, 0, 0), swapRB=False)
    net = _get_fer_net()
    net.setInput(blob)
    probs = _softmax(np.array(net.forward()).reshape(-1))
    label = _FERPLUS_LABELS[int(np.argmax(probs))]
    mapped = EMOTION_MAP.get(label, "neutrality")
    desc = EMOTION_DESCRIPTIONS.get(mapped, "Thanks for sharing how you feel.")
    return mapped, round(float(np.max(probs)), 3), desc


def _analyze_deepface(img: np.ndarray) -> Tuple[str, float, str]:
    from deepface import DeepFace

    try:
        res = DeepFace.analyze(
            img, actions=["emotion"], enforce_detection=True, detector_backend="retinaface", silent=True
        )
        if isinstance(res, list):
            res = res[0]
    except ValueError as ve:
        if "Face could not be detected" in str(ve):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No face detected in the image.") from ve
        raise
    dom = res.get("dominant_emotion", "neutral")
    raw = res.get("emotion", {}).get(dom, 50.0)
    mapped = EMOTION_MAP.get(dom, "neutrality")
    return (
        mapped,
        round(max(0.0, min(1.0, float(raw) / 100.0)), 3),
        EMOTION_DESCRIPTIONS.get(mapped, "Thanks for sharing how you feel."),
    )


def analyze_emotion(base64_img: str) -> Tuple[str, float, str]:
    try:
        img = decode_image_sync(base64_img)
    except ValueError as exc:  # includes binascii.Error from bad base64
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or unreadable image"
        ) from exc

    try:
        # Optional high-accuracy path if the (heavy) deepface package is installed.
        if importlib.util.find_spec("deepface") is not None:
            try:
                return _analyze_deepface(img)
            except HTTPException:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("DeepFace failed, falling back to ONNX models: %s", exc)

        work = _downscale(img)
        faces = _detect_faces(work)
        if not faces:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No face detected in the image.")
        if len(faces) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple faces detected. Please make sure only one face is visible.",
            )
        box = max(faces, key=lambda b: b[2] * b[3])

        if _get_hse_net() is not None:
            try:
                return _analyze_hsemotion(work, box)
            except HTTPException:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("HSEmotion inference failed, using FER+: %s", exc)
        return _analyze_ferplus(work, box)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Emotion analysis failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Image analysis failed"
        ) from exc
