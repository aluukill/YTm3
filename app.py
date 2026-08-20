import os
import re
import time
import uuid
import tempfile
import logging
import threading
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AUDIO_DIR = os.path.join(tempfile.gettempdir(), 'ytm3_audio')
os.makedirs(AUDIO_DIR, exist_ok=True)

AUDIO_FILES = {}
AUDIO_TTL_SECONDS = 3 * 60 * 60

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app, origins=[
    'http://localhost:5000',
    'http://127.0.0.1:5000',
])

AUDIO_MIMETYPES = {
    'm4a': 'audio/mp4',
    'mp4': 'audio/mp4',
    'webm': 'audio/webm',
    'opus': 'audio/ogg',
    'ogg': 'audio/ogg',
    'mp3': 'audio/mpeg',
    'aac': 'audio/aac',
    'flac': 'audio/flac',
    'wav': 'audio/wav',
}


@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')


def _base_ydl_opts(format_selector=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb', 'web'],
            }
        }
    }
    if format_selector:
        opts['format'] = format_selector
    return opts


def _safe_filename(name):
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]+', '_', name).strip() or 'audio'


def _audio_mimetype(ext):
    return AUDIO_MIMETYPES.get(ext.lower(), 'application/octet-stream')


def _prune_audio_files():
    while True:
        time.sleep(60)
        now = time.time()
        expired = [k for k, v in AUDIO_FILES.items() if now - v['created'] > AUDIO_TTL_SECONDS]
        for key in expired:
            entry = AUDIO_FILES.pop(key, None)
            if entry:
                try:
                    os.unlink(entry['path'])
                except OSError:
                    pass


threading.Thread(target=_prune_audio_files, daemon=True).start()

def format_duration(seconds):
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


ERROR_GUESS = {
    'sign in': 'This video requires YouTube sign-in, which is not supported without cookies. Try another video.',
    'not a bot': 'YouTube is blocking the request. Wait a moment and try again, or try another video.',
    'no video formats': 'No downloadable formats found for this video.',
    'no audio stream': 'No audio stream is available for this video.',
    'requested format': 'The requested format is not available. Trying alternative sources...',
    'geo': 'This video is geo-restricted and cannot be accessed from your location.',
}


def friendly_error(msg):
    lower = msg.lower()
    for key, hint in ERROR_GUESS.items():
        if key in lower:
            return hint
    return None


def _extract_info(url, format_selector=None):
    ydl_opts = _base_ydl_opts(format_selector=format_selector)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info and len(info['entries']) > 0:
            info = info['entries'][0]
        return info


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
        duration_str = format_duration(info.get('duration'))
        thumbnail = info.get('thumbnail') or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        return jsonify({
            'id': video_id,
            'title': title,
            'author': uploader,
            'duration': duration_str,
            'thumbnail': thumbnail,
        })
    except Exception as e:
        err = friendly_error(str(e)) or str(e)
        return jsonify({'error': err}), 500


@app.route('/api/download', methods=['POST'])
def download_audio():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    token = uuid.uuid4().hex
    opts = _base_ydl_opts(format_selector='bestaudio/best')
    opts['outtmpl'] = os.path.join(AUDIO_DIR, token + '.%(ext)s')

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]
            filepath = ydl.prepare_filename(info)

        if not os.path.isfile(filepath):
            raise RuntimeError('No audio file was produced.')

        ext = os.path.splitext(filepath)[1].lstrip('.') or 'm4a'
        filename = f"{_safe_filename(info.get('title') or 'audio')}.{ext}"
        AUDIO_FILES[token] = {
            'path': filepath,
            'filename': filename,
            'ext': ext,
            'created': time.time(),
        }

        return jsonify({
            'file_id': token,
            'filename': filename,
            'ext': ext,
            'size': os.path.getsize(filepath),
        })
    except Exception as e:
        err = friendly_error(str(e)) or str(e)
        return jsonify({'error': err}), 500


@app.route('/api/file/<file_id>')
def serve_audio(file_id):
    entry = AUDIO_FILES.get(file_id)
    if not entry or not os.path.isfile(entry['path']):
        return jsonify({'error': 'Audio file expired or not found. Try again.'}), 404

    download = request.args.get('download') == '1'
    return send_file(
        entry['path'],
        mimetype=_audio_mimetype(entry['ext']),
        as_attachment=download,
        download_name=entry['filename'],
        conditional=True,
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
