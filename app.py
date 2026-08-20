import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app, origins=[
    'http://localhost:5000',
    'http://127.0.0.1:5000',
])


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
                'player_client': ['default', 'mweb', 'android', 'web'],
            }
        }
    }
    if format_selector:
        opts['format'] = format_selector
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

        chosen_stream = _find_best_audio_stream(info)
        if not chosen_stream:
            info2 = _extract_info(url, format_selector='bestaudio/best')
            chosen_stream = _find_best_audio_stream(info2)

        stream_url = chosen_stream.get('url') if chosen_stream else None
        ext = chosen_stream.get('ext', 'm4a') if chosen_stream else 'm4a'

        if not stream_url:
            return jsonify({'error': 'No audio stream found'}), 404

        return jsonify({
            'id': video_id,
            'title': title,
            'author': uploader,
            'duration': duration_str,
            'thumbnail': thumbnail,
            'stream_url': stream_url,
            'ext': ext,
        })
    except Exception as e:
        err = friendly_error(str(e)) or str(e)
        return jsonify({'error': err}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
