import os
import subprocess
from flask import Flask, request, render_template, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for flash messages

# Folder configurations
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return '''
    <!doctype html>
    <title>Maxyeu Video Optimizer</title>
    <h2>Upload Video to Optimize</h2>
    <form method=post enctype=multipart/form-data action="/optimize">
      <input type=file name=file required>
      <input type=submit value=Optimize>
    </form>
    '''


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
        
        # Create output file path
        output_filename = f"optimized_{filename}"
        output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
        
        file.save(input_path)

        # High-Speed FFmpeg Command
        command = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # Max speed encoding
            '-crf', '26',            # Optimizes file size and CPU usage
            '-vf', 'scale=1920:-2',  # Downscales width to 1080p, keeps aspect ratio
            '-c:a', 'copy',          # Pass audio directly without re-encoding
            '-threads', '0',         # Auto-utilize available CPU cores
            output_path
        ]

        try:
            # Execute FFmpeg optimization
            subprocess.run(command, check=True)
            
            # Send optimized file back to user
            return send_file(output_path, as_attachment=True)

        except subprocess.CalledProcessError as e:
            flash(f"Error during video processing: {e}")
            return redirect(url_for('index'))
        
        finally:
            # Cleanup temporary upload file
            if os.path.exists(input_path):
                os.remove(input_path)

    flash('File type not allowed')
    return redirect(url_for('index'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
