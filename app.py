import os
import subprocess
from flask import Flask, request, render_template, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Folder configurations
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/optimize', methods=['POST'])
def optimize_video():
    if 'file' not in request.files:
        flash('No file uploaded')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        output_filename = f"optimized_{filename}"
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
        
        file.save(input_path)

        # Retrieve user's method selection and TikTok optimization checkbox from the form
        selected_method = request.form.get('method', 'max_quality')
        tiktok_optimize = request.form.get('tiktok')  # Checkbox value

        # Base CPU-safe command (Forces libx264 and ultrafast to run smoothly on Railway)
        command = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'ultrafast'
        ]

        # Apply specific parameters depending on the selected method
        if selected_method == '720p60':
            command.extend(['-vf', 'scale=1280:720', '-r', '60', '-crf', '26'])
        elif selected_method == 'fps':
            command.extend(['-r', '60', '-crf', '24'])
        else:  # Default: Max Quality + FPS Method
            command.extend(['-vf', 'scale=1920:-2', '-crf', '23'])

        # Apply tighter compression if the TikTok optimization checkbox is checked
        if tiktok_optimize:
            # Adjust CRF/Bitrate lower for smaller file sizes ideal for social media sharing
            command.extend(['-crf', '28'])

        # Finalize audio copy and multi-threading parameters
        command.extend([
            '-c:a', 'copy',
            '-threads', '0',
            output_path
        ])

        try:
            # Execute FFmpeg optimization on CPU
            subprocess.run(command, check=True)
            return send_file(output_path, as_attachment=True)

        except subprocess.CalledProcessError as e:
            flash(f"Error during video processing: {e}")
            return redirect(url_for('index'))
        
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)

    flash('File type not allowed')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
