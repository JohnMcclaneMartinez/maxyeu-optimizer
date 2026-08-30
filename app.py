import os
import time
import threading
from flask import Flask, render_template, request, send_from_directory, flash, redirect, url_for
import ffmpeg
import imageio_ffmpeg

os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

app = Flask(__name__)
app.secret_key = "maxyeu_secret_key"

UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
OUTPUT_FOLDER = os.path.join(app.root_path, 'outputs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER


def cleanup_old_files():
    two_hours_in_seconds = 2 * 3600
    while True:
        now = time.time()
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            if os.path.exists(folder):
                for file_name in os.listdir(folder):
                    file_path = os.path.join(folder, file_name)
                    if os.path.isfile(file_path):
                        if (now - os.path.getmtime(file_path)) > two_hours_in_seconds:
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                print(f"Error deleting {file_path}: {e}")
        time.sleep(900)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/optimize', methods=['POST'])
@app.route('/upload', methods=['POST'])
def optimize_video():
    if 'video' not in request.files:
        flash('No file uploaded.')
        return redirect(url_for('index'))

    file = request.files['video']
    method = request.form.get('method', 'max_quality')
    optimize_tiktok = request.form.get('optimize_tiktok') == 'yes'

    if file.filename == '':
        flash('No file selected.')
        return redirect(url_for('index'))

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    output_filename = f"optimized_{file.filename}"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    
    file.save(input_path)

    try:
        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        
        if method == '720p60':
            crf_val = 22
            scale_filter = 'scale=-2:720'
            preset_val = 'ultrafast'
        elif method == 'fps_patch':
            crf_val = 21
            scale_filter = 'scale=-2:1080'
            preset_val = 'ultrafast'
        else:
            crf_val = 19
            scale_filter = 'scale=-2:1080'
            preset_val = 'superfast'

        output_args = {
            'vcodec': 'libx264',
            'preset': preset_val,
            'crf': crf_val,
            'vf': scale_filter,
            'pix_fmt': 'yuv420p',
            'acodec': 'aac',
            'b:a': '192k'
        }

        if optimize_tiktok:
            output_args['maxrate'] = '8M'
            output_args['bufsize'] = '16M'
            output_args['crf'] = max(crf_val, 23)

        (
            ffmpeg
            .input(input_path)
            .output(output_path, **output_args)
            .overwrite_output()
            .run(cmd=ffmpeg_bin, capture_stdout=True, capture_stderr=True)
        )
        
        return render_template('index.html', download_file=output_filename)

    except Exception as e:
        print(f"Optimization Error: {e}")
        flash('Video optimization failed.')
        return redirect(url_for('index'))


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
