from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import shutil

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DOWNLOAD_DIR = tempfile.gettempdir()
FFMPEG_PATH = shutil.which('ffmpeg')

# yt-dlp options to bypass YouTube bot detection
YDL_BASE = {
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
            'player_skip': ['webpage', 'configs'],
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36',
    },
}

@app.route('/')
def index():
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/privacy.html')
def privacy():
    with open('privacy.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/terms.html')
def terms():
    with open('terms.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/dmca.html')
def dmca():
    with open('dmca.html', 'r', encoding='utf-8') as f:
        return f.read()


@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    ydl_opts = {
        **YDL_BASE,
        'skip_download': True,
    }
    if FFMPEG_PATH:
        ydl_opts['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        seen = set()

        for f in (info.get('formats') or []):
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')
            res = f.get('height')
            fmt_id = f.get('format_id', '')

            if vcodec != 'none' and acodec != 'none' and res:
                label = f"MP4 · {res}p"
                if label not in seen:
                    seen.add(label)
                    formats.append({'label': label, 'format_id': fmt_id, 'type': 'video'})

        formats.sort(key=lambda x: int(x['label'].split('·')[1].strip().replace('p','')) if '·' in x['label'] else 0, reverse=True)
        formats = formats[:5]

        if not formats:
            formats = [
                {'label': 'MP4 · 1080p', 'format_id': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]', 'type': 'video'},
                {'label': 'MP4 · 720p',  'format_id': 'bestvideo[height<=720]+bestaudio/best[height<=720]',   'type': 'video'},
                {'label': 'MP4 · 480p',  'format_id': 'bestvideo[height<=480]+bestaudio/best[height<=480]',   'type': 'video'},
                {'label': 'MP4 · Best',  'format_id': 'bestvideo+bestaudio/best',                             'type': 'video'},
            ]

        audio_formats = [
            {'label': 'MP3 · High Quality (192kbps)', 'format_id': 'audio:bestaudio/best', 'type': 'audio'},
            {'label': 'MP3 · Standard (128kbps)',     'format_id': 'audio:bestaudio[abr<=128]/worstaudio',    'type': 'audio'},
        ]

        return jsonify({
            'title': info.get('title', 'Unknown'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'formats': formats + audio_formats
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download')
def download_video():
    url = request.args.get('url', '').strip()
    format_id = request.args.get('format_id', 'best')
    if not url:
        return jsonify({'error': 'No URL'}), 400

    is_audio = format_id.startswith('audio:')
    actual_fmt = format_id.replace('audio:', '') if is_audio else format_id
    output_tmpl = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')

    base_opts = {
        **YDL_BASE,
        'outtmpl': output_tmpl,
    }
    if FFMPEG_PATH:
        base_opts['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)

    if is_audio:
        if FFMPEG_PATH:
            ydl_opts = {
                **base_opts,
                'format': actual_fmt,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:
            ydl_opts = {**base_opts, 'format': actual_fmt}
    else:
        if FFMPEG_PATH:
            ydl_opts = {
                **base_opts,
                'format': actual_fmt if '+' in actual_fmt else f'bestvideo[height<=1080]+bestaudio/best',
                'merge_output_format': 'mp4',
            }
        else:
            ydl_opts = {
                **base_opts,
                'format': 'best[ext=mp4]/best',
            }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            filename = ydl.prepare_filename(info)

        if is_audio:
            if FFMPEG_PATH:
                mp3 = os.path.splitext(filename)[0] + '.mp3'
                if os.path.exists(mp3):
                    return send_file(mp3, as_attachment=True, download_name=f"{title}.mp3")
            for ext in ['.m4a', '.webm', '.opus', '.mp3', '.ogg']:
                candidate = os.path.splitext(filename)[0] + ext
                if os.path.exists(candidate):
                    return send_file(candidate, as_attachment=True, download_name=f"{title}{ext}")
        else:
            mp4 = os.path.splitext(filename)[0] + '.mp4'
            if os.path.exists(mp4):
                return send_file(mp4, as_attachment=True, download_name=f"{title}.mp4")
            if os.path.exists(filename):
                return send_file(filename, as_attachment=True, download_name=f"{title}.mp4")

        return jsonify({'error': 'File not found after download'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n✅ VidDropper starting on port {port}")
    print(f"🎵 ffmpeg: {'✅ ' + str(FFMPEG_PATH) if FFMPEG_PATH else '⚠️  Not found'}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
