# Deploying MindEase

MindEase is two pieces:

| Piece | What it is | Where it goes |
| --- | --- | --- |
| **Frontend** | Vite + React static site | **Netlify** |
| **Backend** | FastAPI server + WebSocket + ONNX models | **Render** (Docker) |
| **Database** | MongoDB | **MongoDB Atlas** (free tier) |

Netlify can only host the static frontend, so the Python backend runs on Render. The same
`backend/Dockerfile` also works on Railway, Fly.io, or any Docker host if you prefer.

Total time: ~20 minutes. Cost: $0 on free tiers (Render free instances sleep after 15 min idle
and cold-start in ~40s).

---

## 1. MongoDB Atlas (database)

1. Create a free account at <https://www.mongodb.com/atlas> and a free **M0** cluster.
2. **Database Access** -> add a database user (username + password). Save them.
3. **Network Access** -> add IP `0.0.0.0/0` (allow from anywhere). Render's outbound IPs are
   dynamic on the free plan, so this is the simplest option.
4. **Database -> Connect -> Drivers** -> copy the connection string. It looks like:
   `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
   Put your real user/password in place of `USER:PASSWORD`.

## 2. Generate the secrets

Run these locally (any Python 3 with `cryptography` installed, e.g. the backend venv):

```bash
python -c "import secrets; print('JWT_SECRET_KEY =', secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print('DATA_ENCRYPTION_KEY =', Fernet.generate_key().decode())"
```

Also get a **Groq API key** from <https://console.groq.com> (free). Without it the chatbot
still works using built-in offline replies.

> Keep `DATA_ENCRYPTION_KEY` safe. If you lose it, notes / chat messages / DMs written while it
> was set become unreadable.

## 3. Deploy the backend to Render

1. Push this repo to GitHub (the branch you want, e.g. `main`).
2. Render dashboard -> **New + -> Blueprint** -> connect the repo. Render reads `render.yaml`
   and creates the `mindease-backend` web service.
3. Fill in the environment variables it asks for (the `sync: false` ones):
   - `MONGODB_URL` - the Atlas string from step 1
   - `JWT_SECRET_KEY` - from step 2
   - `DATA_ENCRYPTION_KEY` - from step 2
   - `GROQ_API_KEY` - your Groq key
   - `CORS_ORIGINS` - leave as a placeholder for now (e.g. `https://example.com`); you'll fix
     it in step 5
4. Deploy. First build takes a few minutes (it bakes the emotion models into the image).
5. When it's live, note the URL: `https://mindease-backend-XXXX.onrender.com`.
   Check it: `https://mindease-backend-XXXX.onrender.com/health` should return
   `{"status":"ok",...}`.

## 4. Deploy the frontend to Netlify

1. Netlify dashboard -> **Add new site -> Import an existing project** -> pick the repo.
   Netlify reads `frontend/netlify.toml` (base `frontend`, build `npm run build`, publish
   `dist`).
2. Before the first build, add an environment variable:
   **Site configuration -> Environment variables -> Add**
   - Key: `VITE_API_BASE_URL`
   - Value: your Render backend URL, no trailing slash, e.g.
     `https://mindease-backend-XXXX.onrender.com`
3. Deploy. Note the site URL: `https://your-site-name.netlify.app`.

## 5. Point the backend at the frontend (CORS)

1. Back in Render -> `mindease-backend` -> **Environment** -> set
   `CORS_ORIGINS = https://your-site-name.netlify.app` (the exact origin, https, no trailing
   slash). If you later add a custom domain, put both, comma-separated.
2. Save -> Render redeploys automatically.

## 6. Smoke test

Open `https://your-site-name.netlify.app` and:

- Sign up with an email + password -> you should land on the home screen.
- Path selection -> Emotion analysis -> upload a photo of a face -> a mood + confidence shows.
- Chat -> send a message -> a short supportive reply comes back
  (`provider: groq` if your key works, otherwise a local reply).
- (Optional) Community -> Join -> post something; real-time DMs work between two connected
  accounts.

## Notes and limits

- **Cold starts:** the Render free instance sleeps after 15 min of no traffic; the next request
  wakes it (~40s). For always-on, upgrade the instance or add an external uptime pinger.
- **Models:** they are baked into the image at build time. If the build-time download failed
  (network hiccup), the first emotion request downloads them (~30s) and then it's cached until
  the next deploy.
- **Real-time chat runs on one process.** The WebSocket connection manager keeps state in
  memory, so the backend runs with a single worker. Scaling the socket horizontally later needs
  a shared bus (Redis pub/sub).
- **Encryption is on when `DATA_ENCRYPTION_KEY` is set.** It covers emotion notes, chat
  messages, solo journal text, and direct messages. It is transparent to the API - old
  plaintext rows and rows written before the key was set still read fine.
- **Data reset:** to wipe demo data, drop the `mindease` database in Atlas; the backend
  re-seeds the community feed on next start.

## Deploying elsewhere

The backend image is standard. On **Railway**: New Project -> Deploy from repo -> it detects
`backend/Dockerfile` (set the root/context to `backend`); add the same env vars. On **Fly.io**:
`fly launch` inside `backend/`, then `fly secrets set KEY=value ...`. The frontend can go to
Vercel/Cloudflare Pages instead of Netlify - build command `npm run build`, output `dist`,
env var `VITE_API_BASE_URL`, and an SPA rewrite to `/index.html`.
