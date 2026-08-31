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

    # Base FFmpeg command with enlarged probesize for complex video containers
    ffmpeg_cmd = [
        ffmpeg_exe, '-y',
        '-analyzeduration', '100M',
        '-probesize', '100M',
        '-i', input_path
    ]

    # Configure resolution scaling and frame rates safely
    if method == '720p60':
        ffmpeg_cmd.extend(['-vf', 'scale=trunc(iw/2)*2:720', '-r', '60'])
    elif method == 'fps_patch':
        ffmpeg_cmd.extend(['-r', '60'])
    else:  # max_quality (1080p limit, preserving aspect ratio)
        ffmpeg_cmd.extend(['-vf', 'scale=-2:1080'])

    # Codecs and output parameters
    ffmpeg_cmd.extend([
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '22',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-ac', '2'
    ])

    if optimize_tiktok == 'yes':
        ffmpeg_cmd.extend(['-maxrate', '12M', '-bufsize', '16M'])

    ffmpeg_cmd.append(output_path)

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
        # Log clean error details if processing fails
        err_lines = [l for l in e.stderr.split('\n') if 'error' in l.lower() or 'invalid' in l.lower()]
        clean_err = err_lines[-1] if err_lines else "Stream processing failed."

        if os.path.exists(input_path):
            os.remove(input_path)
            
        return jsonify({'success': False, 'error': f"FFmpeg Processing Error: {clean_err}"}), 500

    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
