import os
import time
import threading
from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for
import ffmpeg
import static_ffmpeg

# Initialize static-ffmpeg to install/load FFmpeg binaries automatically on Render
static_ffmpeg.add_paths()

app = Flask(__name__)
app.secret_key = "maxyeu_secret_key"

# Configuration paths
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
OUTPUT_FOLDER = os.path.join(app.root_path, 'outputs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


# ==========================================
# 1. Background Cleanup (Deletes > 2 Hours)
# ==========================================
def cleanup_old_files():
    """Checks every 15 minutes and deletes files older than 2 hours (7,200 seconds)."""
    two_hours_in_seconds = 2 * 3600

    while True:
        now = time.time()
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            if os.path.exists(folder):
                for file_name in os.listdir(folder):
                    file_path = os.path.join(folder, file_name)
                    if os.path.isfile(file_path):
                        file_age = now - os.path.getmtime(file_path)
                        if file_age > two_hours_in_seconds:
                            try:
                                os.remove(file_path)
                                print(f"Deleted old file: {file_path}")
                            except Exception as e:
                                print(f"Error deleting {file_path}: {e}")
        
        # Check every 15 minutes (900 seconds) for prompt cleanup
        time.sleep(900)

# Start background cleanup thread automatically
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()


# ==========================================
# 2. Flask Web Routes
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/optimize', methods=['POST'])
def optimize_video():
    if 'video' not in request.files:
        flash('No file uploaded.')
        return redirect(url_for('index'))

    file = request.files['video']
    if file.filename == '':
        flash('No file selected.')
        return redirect(url_for('index'))

    # Save incoming upload
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    output_filename = f"optimized_{file.filename}"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    file.save(input_path)

    try:
        # Fast, low-RAM compression for Render's free tier
        (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                vcodec='libx264',
                preset='ultrafast',
                crf=28,
                vf='scale=-2:720'
            )
            .overwrite_output()
            .run()
        )
        return render_template('index.html', download_file=output_filename)

    except Exception as e:
        print(f"Optimization Error: {e}")
        flash('Video optimization failed. Please ensure the file format is supported.')
        return redirect(url_for('index'))


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)