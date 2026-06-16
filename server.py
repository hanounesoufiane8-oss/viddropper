from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DOWNLOAD_DIR = tempfile.gettempdir()

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

    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        seen = set()

        for f in (info.get('formats') or []):
            ext = f.get('ext', '')
            res = f.get('height')
            vcodec = f.get('vcodec', 'none')
            fmt_id = f.get('format_id', '')

            if ext == 'mp4' and vcodec != 'none' and res:
                label = f"MP4 · {res}p"
                if label not in seen:
                    seen.add(label)
                    formats.append({'label': label, 'format_id': fmt_id})

        def res_key(x):
            try: return int(x['label'].split('·')[1].strip().replace('p',''))
            except: return 0

        formats.sort(key=res_key, reverse=True)
        formats = formats[:5]
        formats.append({'label': 'MP3 · Audio only', 'format_id': 'bestaudio/best'})

        return jsonify({
            'title': info.get('title', 'Unknown'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'formats': formats
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download')
def download_video():
    url = request.args.get('url', '').strip()
    format_id = request.args.get('format_id', 'best')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    output_path = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')
    is_audio = format_id == 'bestaudio/best'

    if is_audio:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'quiet': True,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        }
    else:
        ydl_opts = {'format': format_id, 'outtmpl': output_path, 'quiet': True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            ext = 'mp3' if is_audio else info.get('ext', 'mp4')
            filename = ydl.prepare_filename(info)
            if is_audio:
                filename = os.path.splitext(filename)[0] + '.mp3'

        if os.path.exists(filename):
            return send_file(filename, as_attachment=True, download_name=f"{title}.{ext}")
        return jsonify({'error': 'File not found after download'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print('\n VidDropper server starting...')
    print(f' Running on port {port}\n')
    app.run(debug=False, host='0.0.0.0', port=port)
