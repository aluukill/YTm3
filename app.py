import os
import re
import urllib.parse
import tempfile
import atexit
import shutil
from flask import Flask, request, jsonify, send_from_directory, Response
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yt_dlp

app = Flask(__name__, static_folder='.')

COOKIE_FILE = None
if os.path.exists('cookies.txt'):
    dst = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
    shutil.copy2('cookies.txt', dst.name)
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
    'Connection': 'keep-alive'
})

CHUNK_SIZE = 1048576  # 1MB

def format_duration(seconds):
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extract_flat': False
    }
    if os.path.exists(COOKIE_FILE):
        ydl_opts['cookiefile'] = COOKIE_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

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
        return jsonify({'error': str(e)}), 500

@app.route('/api/download')
def download_audio():
    url = request.args.get('url', '').strip()

    if not url:
        return "URL parameter missing", 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    if os.path.exists(COOKIE_FILE):
        ydl_opts['cookiefile'] = COOKIE_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            title = info.get('title', 'audio')
            clean_title = re.sub(r'[^\w\s-]', '', title).strip() or 'audio'
            
            formats = info.get('formats', [])
            audio_streams = [f for f in formats if f.get('vcodec') == 'none' and f.get('url')]
            
            if not audio_streams:
                return "No audio stream found", 404

            audio_streams.sort(key=lambda x: x.get('abr') or x.get('tbr') or 0, reverse=True)
            chosen_stream = audio_streams[0]
            stream_url = chosen_stream.get('url')
            ext = chosen_stream.get('ext', 'm4a')

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
        return f"Error downloading audio: {str(e)}", 500

@app.route('/api/stream')
def stream_audio():
    url = request.args.get('url', '').strip()
    if not url:
        return "URL parameter missing", 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    if os.path.exists(COOKIE_FILE):
        ydl_opts['cookiefile'] = COOKIE_FILE

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            formats = info.get('formats', [])
            audio_streams = [f for f in formats if f.get('vcodec') == 'none' and f.get('url')]
            if not audio_streams:
                return "No stream found", 404

            audio_streams.sort(key=lambda x: x.get('abr') or x.get('tbr') or 0, reverse=True)
            stream_url = audio_streams[0].get('url')
            ext = audio_streams[0].get('ext', 'm4a')

            r = session.get(stream_url, stream=True, timeout=30)
            return Response(r.iter_content(chunk_size=CHUNK_SIZE), content_type=f'audio/{ext}')
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
