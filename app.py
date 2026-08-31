import os
import subprocess
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

    # Save uploaded file safely
    input_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(input_path)

    output_filename = f"optimized_{file.filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    # Base FFmpeg command setup
    ffmpeg_cmd = ['ffmpeg', '-y', '-i', input_path]

    # Apply processing presets based on selected method
    if method == '720p60':
        ffmpeg_cmd.extend(['-vf', 'scale=-2:720', '-r', '60', '-c:v', 'libx264', '-crf', '22', '-preset', 'fast'])
    elif method == 'fps_patch':
        ffmpeg_cmd.extend(['-r', '60', '-c:v', 'libx264', '-crf', '20', '-preset', 'fast'])
    else:  # max_quality
        ffmpeg_cmd.extend(['-vf', 'scale=-2:1080', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium'])

    if optimize_tiktok == 'yes':
        ffmpeg_cmd.extend(['-maxrate', '12M', '-bufsize', '16M'])

    ffmpeg_cmd.extend(['-c:a', 'aac', '-b:a', '192k', output_path])

    try:
        # Run encoding on server
        subprocess.run(ffmpeg_cmd, check=True)

        # Cleanup input file to save disk space on Railway
        if os.path.exists(input_path):
            os.remove(input_path)

        # Send JSON response back to JS frontend
        return jsonify({
            'success': True,
            'download_url': url_for('download_file', filename=output_filename)
        })

    except subprocess.CalledProcessError as e:
        if os.path.exists(input_path):
            os.remove(input_path)
        return jsonify({'success': False, 'error': 'FFmpeg processing failed'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
