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
Your Browser  ──►  Flask + yt-dlp  ──►  YouTube
localhost:5000        (runs locally)       Home IP
```

The entire app runs locally on your machine. All YouTube requests originate from your home IP — no cookies, tokens, or cloud accounts required.

---

## Tech Stack

- **Backend**: Python, Flask, Flask-CORS, `yt-dlp`
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

### 2. Run the app

```bash
python app.py
```

### 3. Open in your browser

Visit [http://localhost:5000](http://localhost:5000) — paste a YouTube URL and download the audio. The app serves both the frontend and the API from the same local server.

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
├── app.py              # Flask app: API server, yt-dlp wrapper & static frontend
├── index.html          # Frontend
├── style.css           # Styles
├── script.js           # Client-side logic
├── logo.png            # Logo
├── requirements.txt    # Python dependencies
├── .gitignore
└── README.md
```

---

## License

[MIT](LICENSE)