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

    # Build video filter chain dynamically
    vf_filters = []
    
    if method == '720p60':
        vf_filters.append('scale=-2:720')
        vf_filters.append('fps=60')
    elif method == 'fps_patch':
        vf_filters.append('fps=60')
    else:  # max_quality
        vf_filters.append('scale=-2:1080')

    # Construct strict FFmpeg command structure
    ffmpeg_cmd = [
        ffmpeg_exe, '-y',
        '-i', input_path,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '22'
    ]

    # Add video filters if defined
    if vf_filters:
        ffmpeg_cmd.extend(['-vf', ','.join(vf_filters)])

    # Handle TikTok bitrate constraints safely
    if optimize_tiktok == 'yes':
        ffmpeg_cmd.extend(['-maxrate', '12M', '-bufsize', '16M'])

    # Audio settings & output path
    ffmpeg_cmd.extend([
        '-c:a', 'aac',
        '-b:a', '192k',
        output_path
    ])

    try:
        # Run FFmpeg process
        process = subprocess.run(
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
        # Extract meaningful error details from stdout/stderr
        err_msg = e.stderr.strip() if e.stderr else "Unknown encoding error"
        filtered_lines = [line for line in err_msg.split('\n') if "error" in line.lower() or "invalid" in line.lower()]
        final_error = filtered_lines[-1] if filtered_lines else err_msg[-200:]

        if os.path.exists(input_path):
            os.remove(input_path)
            
        return jsonify({'success': False, 'error': f"FFmpeg Error: {final_error}"}), 500

    except Exception as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
