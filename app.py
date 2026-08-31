import os
import subprocess
import traceback
import imageio_ffmpeg
from flask import Flask, render_template, request, jsonify, send_from_directory, url_for

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'processed'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize():
    if 'video' not in request.files:
        return jsonify({'success': False, 'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400

    method = request.form.get('method', 'max_quality')
    optimize_tiktok = request.form.get('optimize_tiktok')

    input_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(input_path)

    output_filename = f"optimized_{file.filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Configure low-memory resolution limits
    if method == '720p60':
        scale_filter = 'scale=trunc(iw/2)*2:720,fps=60'
    elif method == 'fps_patch':
        scale_filter = 'fps=60'
    else:  # max_quality capped at 1080p
        scale_filter = 'scale=trunc(iw/2)*2:min(1080\,ih)'

    # Memory-safe FFmpeg configuration
    ffmpeg_cmd = [
        ffmpeg_exe, '-y',
        '-threads', '2',                # Cap threads to prevent RAM spikes
        '-i', input_path,
        '-vf', scale_filter,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',        # Ultrafast uses the least RAM
        '-crf', '24',                   # Slightly lighter compression
        '-pix_fmt', 'yuv420p'
    ]

    if optimize_tiktok == 'yes':
        ffmpeg_cmd.extend(['-maxrate', '8M', '-bufsize', '8M'])

    ffmpeg_cmd.extend([
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ac', '2',
        output_path
    ])

    try:
        res = subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if res.returncode != 0:
            err_log = "\n".join(res.stderr.strip().split('\n')[-5:])
            raise Exception(f"FFmpeg error code {res.returncode}: {err_log}")

        if os.path.exists(input_path):
            os.remove(input_path)

        return jsonify({
            'success': True,
            'download_url': url_for('download_file', filename=output_filename)
        })

    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
