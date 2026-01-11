from flask import Flask, render_template, request, jsonify, Response, send_file
import requests
from scraper import parse_rednote_url
import io
import zipfile
import time

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/get-info', methods=['POST'])
def get_info():
    data = request.json
    result = parse_rednote_url(data.get('url'))
    if "error" in result: return jsonify(result), 400
    return jsonify(result)

# Proxy Image (Quan trọng cho Avatar & Ảnh)
@app.route('/proxy-image')
def proxy_image():
    url = request.args.get('url')
    if not url: return "", 404
    try:
        # Headers tối giản để load ảnh nhanh hơn
        headers = { "User-Agent": "Mozilla/5.0", "Referer": "https://www.xiaohongshu.com/" }
        resp = requests.get(url, headers=headers, stream=True, timeout=5)
        return Response(resp.iter_content(chunk_size=1024), content_type=resp.headers.get('Content-Type'))
    except: return "", 404

# Proxy Download (Video)
@app.route('/proxy-download')
def proxy_download():
    url = request.args.get('url')
    filename = request.args.get('filename', 'file.mp4')
    def generate():
        try:
            headers = { "User-Agent": "Mozilla/5.0", "Referer": "https://www.xiaohongshu.com/" }
            with requests.get(url, headers=headers, stream=True) as r:
                r.raise_for_status()
                for chunk in r.iter_content(chunk_size=8192): yield chunk
        except: pass
    return Response(generate(), headers={
        'Content-Disposition': f'attachment; filename={filename}',
        'Content-Type': 'application/octet-stream'
    })

# Download ZIP (PC)
@app.route('/download-zip', methods=['POST'])
def download_zip():
    data = request.json
    image_urls = data.get('images', [])
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        headers = { "User-Agent": "Mozilla/5.0", "Referer": "https://www.xiaohongshu.com/" }
        for idx, url in enumerate(image_urls):
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    zip_file.writestr(f"image_{idx+1}.jpg", resp.content)
            except: continue
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name=f'rednote_album_{int(time.time())}.zip')

if __name__ == '__main__':
    app.run(debug=True, port=5000)