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

    # Build video filter parameter
    if method == '720p60':
        vf_param = 'scale=trunc(iw/2)*2:720,fps=60'
    elif method == 'fps_patch':
        vf_param = 'fps=60'
    else:  # max_quality
        vf_param = 'scale=trunc(iw/2)*2:min(1080\,ih)'

    # Construct clean FFmpeg command sequence
    ffmpeg_cmd = [
        ffmpeg_exe, '-y',
        '-i', input_path,
        '-vf', vf_param,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '22',
        '-pix_fmt', 'yuv420p'
    ]

    # Insert TikTok bitrate capping inline before audio flags
    if optimize_tiktok == 'yes':
        ffmpeg_cmd.extend(['-maxrate', '12M', '-bufsize', '16M'])

    # Audio settings & target file path
    ffmpeg_cmd.extend([
        '-c:a', 'aac',
        '-b:a', '192k',
        '-ac', '2',
        output_path
    ])

    try:
        subprocess.run(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        if os.path.exists(input_path):
            os.remove(input_path)

        return jsonify({
            'success': True,
            'download_url': url_for('download_file', filename=output_filename)
        })

    except subprocess.CalledProcessError as e:
        # Return full raw stderr so we can pinpoint any remaining flag issues
        raw_error = e.stderr.strip() if e.stderr else "Unknown FFmpeg error"
        
        if os.path.exists(input_path):
            os.remove(input_path)
            
        return jsonify({'success': False, 'error': f"FFmpeg detail: {raw_error[-300:]}"}), 500

    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
