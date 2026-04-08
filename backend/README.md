# MindEase Backend (FastAPI + MongoDB + Free AI Fallback)

## 1) Setup

1. Install **Python 3.11** and MongoDB locally.
   - macOS (Homebrew): `brew install python@3.11`
   - or Conda: `conda create -n mindease-backend python=3.11 -y && conda activate mindease-backend`
2. From `backend/` create and activate a virtual environment using Python 3.11.
3. Install dependencies:
   ```bash
   python3.11 -m pip install -r requirements.txt
   ```
4. Configure environment:
   ```bash
   cp .env.example .env
   ```
5. Update `.env` values (especially `JWT_SECRET_KEY`).

## 2) Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

If you see `ModuleNotFoundError: fastapi` or TensorFlow install errors, your environment is likely not Python 3.11.

## 3) AI Provider Fallback

Provider priority:
1. HuggingFace Inference API (`HF_API_TOKEN`, `HF_MODEL`)
2. Ollama local server (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`)
3. GPT4All local model (`GPT4ALL_MODEL_PATH`)

If one provider fails, the backend automatically tries the next.

## 4) Key Routes

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/logout` (protected)
- `GET /api/auth/me` (protected)
- `POST /api/emotion/detect` (protected, supports both `multipart/form-data` and `application/json`)
- `GET /api/emotion/history` (protected)
- `POST /api/chat/send` (protected)
- `POST /api/community/join` (protected)
- `POST /api/connection/add` (protected)
- `POST /api/feedback/submit` (protected)

## 5) Sample API Calls

### Signup
```bash
curl -X POST "http://localhost:8000/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"name":"Tejas","email":"tejas@example.com","password":"StrongPass123"}'
```

### Login
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"tejas@example.com","password":"StrongPass123"}'
```

### Emotion Detect (file upload + reason)
```bash
curl -X POST "http://localhost:8000/api/emotion/detect" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "image_file=@/absolute/path/to/face.jpg" \
  -F "reason=I feel nervous before presentation"
```

### Emotion Detect (camera base64 + reason)
```bash
curl -X POST "http://localhost:8000/api/emotion/detect" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"image_base64":"data:image/jpeg;base64,<BASE64_IMAGE>","reason":"I feel low today"}'
```

## 6) Frontend Camera Permission Flow

Use an explicit permission-first flow in frontend:

1. User clicks **Analyse My Emotions**
2. Call `navigator.mediaDevices.getUserMedia({ video: true })`
3. Show live preview only after permission is granted
4. Capture a single frame when user clicks capture
5. Stop camera tracks immediately after capture
6. Send image to `POST /api/emotion/detect`

Example frontend logic:

```javascript
const stream = await navigator.mediaDevices.getUserMedia({ video: true });
video.srcObject = stream;

// on Capture click:
canvas.width = video.videoWidth;
canvas.height = video.videoHeight;
canvas.getContext("2d").drawImage(video, 0, 0);
const imageBase64 = canvas.toDataURL("image/jpeg", 0.9);

stream.getTracks().forEach((track) => track.stop());

await fetch("http://localhost:8000/api/emotion/detect", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  },
  body: JSON.stringify({ image_base64: imageBase64, reason: "optional reason" }),
});
```

### Emotion History
```bash
curl -X GET "http://localhost:8000/api/emotion/history" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### AI Chat
```bash
curl -X POST "http://localhost:8000/api/chat/send" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"message":"I am anxious about tomorrow.","emotion_context":"fear"}'
```

### Join Community
```bash
curl -X POST "http://localhost:8000/api/community/join" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"community_name":"public-speaking-support"}'
```

### Add Connection
```bash
curl -X POST "http://localhost:8000/api/connection/add" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"target_user_email":"friend@example.com"}'
```

### Submit Feedback (without flow example)
```bash
curl -X POST "http://localhost:8000/api/feedback/submit" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"flow_type":"without_flow","content_type":"quotes","message":"Helpful content","rating":5}'
```
