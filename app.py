import os
import subprocess
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_flash'

# Configure upload and processed folders
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
PROCESSED_FOLDER = os.path.join(os.getcwd(), 'processed')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'mp4', 'mov', 'mkv', 'avi', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 1. LANDING / HOME PAGE ROUTE
@app.route('/')
def home():
    return render_template('home.html')

# 2. VIDEO PROCESSOR TOOL ROUTE
@app.route('/app')
def processor():
    return render_template('index.html')

# 3. VIDEO PROCESSING ENDPOINT
@app.route('/optimize', methods=['POST'])
def optimize():
    if 'video' not in request.files:
        flash('No video file provided')
        return redirect(url_for('processor'))

    file = request.files['video']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('processor'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(input_path)

        output_filename = f"optimized_{filename}"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)

        # Get settings from form
        method = request.form.get('method', 'speed')
        
        # FFmpeg low-RAM baseline configuration
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '26',
            '-vf', 'scale=-2:1080',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-threads', '2',
            output_path
        ]

        try:
            subprocess.run(ffmpeg_cmd, check=True)
            return send_file(output_path, as_attachment=True)
        except subprocess.CalledProcessError as e:
            flash(f'Error processing video: {str(e)}')
            return redirect(url_for('processor'))

    flash('Invalid file extension')
    return redirect(url_for('processor'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
