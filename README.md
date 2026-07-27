# YTm3 — YouTube Audio Converter & Downloader

A lightweight web application to download audio from YouTube videos in maximum available quality. Built with Flask, `yt-dlp`, and vanilla HTML/CSS/JS.

<p align="center">
  <img src="logo.png" alt="YTm3 Logo" height="200" />
</p>

## Features

- **Max Quality Extraction** — Automatically streams the highest available bitrate audio from YouTube.
- **Universal Link Support** — Videos, shorts, live streams, and music.youtube.com.
- **Audio Preview** — Built-in HTML5 player for previewing before download.
- **Download History** — Recent conversions saved in browser localStorage.
- **Minimal UI** — Clean, light-mode interface.

---

## Architecture

```
Vercel (Frontend)  ──API──►  Your PC (Backend)  ──►  YouTube
ytm3.vercel.app              Flask + yt-dlp             Home IP
```

- **Frontend** is hosted on Vercel (static files).
- **Backend** runs on your PC, exposed via Cloudflare Tunnel.
- All YouTube requests originate from your home IP — no cloud-IP blocks.

---

## Tech Stack

- **Backend**: Python, Flask, Flask-CORS, `yt-dlp`, `requests`
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Icons & Typography**: Font Awesome 6, Google Fonts (Poppins)

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/aluukill/YTm3.git
cd YTm3
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. YouTube cookies

Export your YouTube cookies in Netscape format using a browser extension ([Chrome](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid), [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)) and save as `COOKIES.txt` in the project root.

### 3. Run the backend

```bash
python app.py
```

### 4. Expose to internet (Cloudflare Tunnel)

Download [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) and run:

```bash
cloudflared tunnel --url http://localhost:5000
```

This gives you a public URL like `https://xxx.trycloudflare.com`.

### 5. Configure the frontend

Edit `config.js` with your tunnel URL:

```js
const BACKEND_URL = "https://xxx.trycloudflare.com";
```

### 6. Deploy frontend to Vercel

Push to GitHub, import the repo on [vercel.com](https://vercel.com). It auto-deploys as a static site.

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/status` | Health check |
| `POST` | `/api/info` | Fetch video metadata + direct stream URL |

The `/api/info` response includes a `stream_url` field pointing directly to YouTube's CDN. The browser downloads audio straight from YouTube — no proxying through the backend.

---

## Project Structure

```
YTm3/
├── app.py              # Flask API server & yt-dlp wrapper
├── config.js           # Backend URL for frontend
├── index.html          # Frontend
├── style.css           # Styles
├── script.js           # Client-side logic
├── COOKIES.txt         # YouTube session cookies
├── logo.png            # Logo
├── vercel.json         # Vercel static deployment config
├── requirements.txt    # Python dependencies
├── .gitignore
└── README.md
```

---

## License

[MIT](LICENSE)
