import os
import re
import urllib.parse
import tempfile
import atexit
import shutil
import logging
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
CORS(app, origins=[
    'https://ytm3.vercel.app',
    'http://localhost:5000',
    'http://127.0.0.1:5000',
])

COOKIE_FILE = None
if os.path.exists('COOKIES.txt'):
    dst = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    shutil.copy2('COOKIES.txt', dst.name)
    dst.close()
    COOKIE_FILE = dst.name
    atexit.register(lambda p=COOKIE_FILE: os.unlink(p))

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retry)
session.mount('https://', adapter)
session.mount('http://', adapter)
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'ngrok-skip-browser-warning': 'true',
})

CHUNK_SIZE = 1048576


def _base_ydl_opts(format_selector=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['default', 'mweb', 'android', 'web'],
            }
        }
    }
    if format_selector:
        opts['format'] = format_selector
    if COOKIE_FILE and os.path.exists(COOKIE_FILE):
        opts['cookiefile'] = COOKIE_FILE
    return opts

def format_duration(seconds):
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


ERROR_GUESS = {
    'sign in': 'YouTube cookies have expired or are invalid. Please export fresh cookies from your browser and replace COOKIES.txt.',
    'not a bot': 'YouTube is blocking requests due to suspected bot activity. Please export fresh cookies from your browser and replace COOKIES.txt.',
    'no video formats': 'No downloadable formats found for this video.',
    'no audio stream': 'No audio stream is available for this video.',
    'requested format': 'The requested format is not available. Trying alternative sources...',
    'geo': 'This video is geo-restricted and cannot be accessed with the current cookies.',
}


def friendly_error(msg):
    lower = msg.lower()
    for key, hint in ERROR_GUESS.items():
        if key in lower:
            return hint
    return None


def _find_best_audio_stream(info):
    formats = info.get('formats', [])

    streams = [f for f in formats if f.get('vcodec') == 'none' and f.get('url')]
    if streams:
        streams.sort(key=lambda x: x.get('abr') or x.get('tbr') or 0, reverse=True)
        return streams[0]

    streams = [f for f in formats if f.get('acodec') and f.get('acodec') != 'none' and f.get('url')]
    if streams:
        streams.sort(key=lambda x: x.get('abr') or x.get('tbr') or 0, reverse=True)
        return streams[0]

    streams = [f for f in formats if f.get('url')]
    if streams:
        streams.sort(key=lambda x: x.get('tbr') or 0, reverse=True)
        return streams[0]

    return None


def _extract_info(url, format_selector=None):
    ydl_opts = _base_ydl_opts(format_selector=format_selector)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info and len(info['entries']) > 0:
            info = info['entries'][0]
        return info


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/status')
def api_status():
    return jsonify({'status': 'ok'})


@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        info = _extract_info(url)

        video_id = info.get('id')
        title = info.get('title')
        uploader = info.get('uploader') or info.get('channel') or 'YouTube Creator'
        duration_sec = info.get('duration')
        duration_str = format_duration(duration_sec)
        thumbnail = info.get('thumbnail') or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        audio_formats = []
        formats = info.get('formats', [])
        for f in formats:
            if f.get('vcodec') == 'none' and f.get('url'):
                ext = f.get('ext', 'm4a')
                abr = f.get('abr') or f.get('tbr') or 128
                audio_formats.append({
                    'format_id': f.get('format_id'),
                    'ext': ext,
                    'abr': int(abr),
                    'filesize': f.get('filesize') or f.get('filesize_approx') or 0
                })

        audio_formats.sort(key=lambda x: x['abr'], reverse=True)

        return jsonify({
            'id': video_id,
            'title': title,
            'author': uploader,
            'duration': duration_str,
            'thumbnail': thumbnail,
            'formats': audio_formats
        })
    except Exception as e:
        err = friendly_error(str(e)) or str(e)
        return jsonify({'error': err}), 500

@app.route('/api/download')
def download_audio():
    url = request.args.get('url', '').strip()

    if not url:
        return "URL parameter missing", 400

    try:
        info = _extract_info(url)

        title = info.get('title', 'audio')
        clean_title = re.sub(r'[^\w\s-]', '', title).strip() or 'audio'

        chosen_stream = _find_best_audio_stream(info)

        if not chosen_stream:
            try:
                info2 = _extract_info(url, format_selector='bestaudio/best')
                if info2.get('requested_formats'):
                    chosen_stream = info2['requested_formats'][0]
                elif info2.get('url'):
                    chosen_stream = info2
            except Exception:
                pass

        if not chosen_stream:
            return "No audio stream found", 404

        stream_url = chosen_stream.get('url')
        ext = chosen_stream.get('ext', 'm4a')

        if not stream_url:
            return "No stream URL found", 404

        r = session.get(stream_url, stream=True, timeout=30)

        def generate():
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    yield chunk

        filename = f"{clean_title}.{ext}"
        encoded_filename = urllib.parse.quote(filename)

        headers = {
            'Content-Type': f'audio/{ext}',
            'Content-Disposition': f'attachment; filename="{encoded_filename}"; filename*=UTF-8\'\'{encoded_filename}'
        }

        return Response(generate(), headers=headers, status=200)

    except Exception as e:
        err = friendly_error(str(e)) or str(e)
        return f"Error downloading audio: {err}", 500

@app.route('/api/stream')
def stream_audio():
    url = request.args.get('url', '').strip()
    if not url:
        return "URL parameter missing", 400

    try:
        info = _extract_info(url)

        chosen_stream = _find_best_audio_stream(info)

        if not chosen_stream:
            try:
                info2 = _extract_info(url, format_selector='bestaudio/best')
                if info2.get('requested_formats'):
                    chosen_stream = info2['requested_formats'][0]
                elif info2.get('url'):
                    chosen_stream = info2
            except Exception:
                pass

        if not chosen_stream:
            return "No stream found", 404

        stream_url = chosen_stream.get('url')
        ext = chosen_stream.get('ext', 'm4a')

        if not stream_url:
            return "No stream URL found", 404

        r = session.get(stream_url, stream=True, timeout=30)
        return Response(r.iter_content(chunk_size=CHUNK_SIZE), content_type=f'audio/{ext}')
    except Exception as e:
        err = friendly_error(str(e)) or str(e)
        return err, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
