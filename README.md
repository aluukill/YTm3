# YTm3 — YouTube Audio Converter & Downloader

A lightweight, high-performance web application to convert and download audio from YouTube videos in maximum available quality. Built with Python (Flask), `yt-dlp`, and modern Vanilla HTML5/CSS3/JavaScript.

<p align="center">
  <img src="logo.png" alt="YTm3 Logo" height="200" />
</p>
## Features

- **Max Quality Extraction**: Automatically detects and streams the highest available bitrate audio directly from YouTube.
- **Universal YouTube Link Support**: Robust URL parsing handles videos, shorts, live streams, `music.youtube.com`, and playlist URLs cleanly.
- **Audio Stream Preview**: Built-in HTML5 player lets users preview the extracted audio before downloading.
- **Pill-Rounded Minimalist UI**: Clean, light-mode interface with zero clutter.
- **Recent Download History**: Saves your converted tracks locally in your browser's `localStorage`.
- **Production Ready**: Configured for WSGI servers (`gunicorn`) with dynamic port binding for cloud deployments.

---

## Architecture

```
┌─────────────────────┐         ┌─────────────────────────────┐
│   Vercel (Frontend) │  ──►   │   Your PC (Backend)         │
│   ytm3.vercel.app   │  API   │   Flask + yt-dlp + ngrok    │
│   index.html        │  calls │   YouTube requests go from   │
│   script.js         │         │   your home IP               │
│   style.css         │         │                               │
└─────────────────────┘         └─────────────────────────────┘
```

The frontend is hosted on Vercel. The backend runs on your PC and is exposed to the internet via a tunnel (ngrok / Cloudflare Tunnel). This way, all YouTube API requests originate from your home IP, avoiding cloud-IP blocks.

---

## Tech Stack

- **Backend**: Python 3.10+, Flask, Flask-CORS, `yt-dlp`, `requests`, `gunicorn`
- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System), JavaScript (ES6+)
- **Icons & Typography**: Font Awesome 6, Google Fonts (Poppins)

---

## Quick Start (Local Development)

### 1. Clone the repository

```bash
git clone https://github.com/aluukill/YTm3.git
cd YTm3
```

### 2. Set up a virtual environment (optional but recommended)

```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure YouTube cookies (required)

YouTube blocks unauthenticated requests. You must provide a `COOKIES.txt` file with your YouTube session cookies so `yt-dlp` can authenticate.

1. Install a browser extension:
   - [Get COOKIES.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid) (Chrome)
   - [COOKIES.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) (Firefox)
2. Log into **youtube.com** in your browser.
3. Use the extension to export your cookies for `youtube.com` in **Netscape format**.
4. Save the exported file as **`COOKIES.txt`** in the project root directory.

> A pre-configured `COOKIES.txt` is included in the repository. If yours expires, replace it with a fresh export.

### 5. Run the development server

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your web browser.

---

## Hybrid Deployment (Vercel + Your PC)

This is the recommended setup. The frontend runs on Vercel while your PC serves as the backend, using your home IP for YouTube requests.

### Step 1 — Deploy frontend to Vercel

1. Push your repo to GitHub.
2. Go to [vercel.com](https://vercel.com), import the repo.
3. Vercel will detect the static frontend and deploy it to `ytm3.vercel.app`.
4. No special build settings needed — `vercel.json` handles this automatically.

### Step 2 — Run backend on your PC

```bash
pip install -r requirements.txt
python app.py
```

The Flask server starts on `http://localhost:5000`.

### Step 3 — Expose your PC to the internet

Use **ngrok** or **Cloudflare Tunnel** to give your local server a public URL:

**Option A — ngrok:**
```bash
ngrok http 5000
```
This gives you a URL like `https://abc123.ngrok-free.app`.

**Option B — Cloudflare Tunnel:**
```bash
cloudflared tunnel --url http://localhost:5000
```
This gives you a URL like `https://your-tunnel.trycloudflare.com`.

### Step 4 — Update frontend config

Edit `config.js` and set your tunnel URL:

```js
const BACKEND_URL = "https://abc123.ngrok-free.app";
```

Commit and push. Vercel auto-deploys. Your frontend now sends API requests to your PC.

---

## Local Development (Full Stack on One Machine)

When `BACKEND_URL` is empty in `config.js`, the frontend uses relative paths (`/api/...`) and the Flask server serves everything. This is the default for local development.

---

## API Reference

### `GET /api/status`

Health check endpoint. Returns `{"status": "ok"}`.

### `POST /api/info`

Fetches video metadata (title, author, thumbnail, duration, audio streams).

- **Body**: `{"url": "https://www.youtube.com/watch?v=..."}`
- **Response**: JSON metadata object.

### `GET /api/stream`

Streams the raw highest quality audio for inline HTML5 preview.

- **Query Param**: `?url=...`

### `GET /api/download`

Downloads the highest quality audio track as a file attachment.

- **Query Param**: `?url=...`

---

## Project Structure

```text
YTm3/
├── app.py              # Flask backend server & yt-dlp wrapper
├── config.js           # Backend URL configuration for frontend
├── index.html          # Frontend web layout
├── style.css           # Custom CSS design system
├── script.js           # Client-side logic & API integration
├── COOKIES.txt         # YouTube session cookies (Netscape format)
├── logo.png            # App logo asset
├── vercel.json         # Vercel deployment config (static frontend)
├── requirements.txt    # Python dependencies
├── Procfile            # Deployment process definition
├── .gitignore          # Git exclusion rules
└── README.md           # Documentation
```

---

## License

This project is open-source and available under the [MIT License](LICENSE).
