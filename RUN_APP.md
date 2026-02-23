# How to run the app

## Backend (port 8000)

**Terminal 1:**
```bash
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or from project root:
```bash
./backend/start_backend.sh
```

Leave this running.

---

## Frontend (port 3000)

**Terminal 2:**
```bash
cd frontend && npm run dev
```

Then open **http://localhost:3000** in your browser.

---

## One-liners from project root

- Backend: `./backend/start_backend.sh`
- Frontend: `cd frontend && npm run dev`

Backend must be running before you use the app (frontend proxies `/api` to port 8000).
