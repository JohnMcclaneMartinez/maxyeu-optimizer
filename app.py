import os
import re
import time
import subprocess
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

progress_tracker = {}


def cleanup_old_files(max_age_seconds=3600):
    """Deletes files older than 1 hour from uploads and outputs."""
    now = time.time()
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                if now - os.path.getmtime(file_path) > max_age_seconds:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error removing {file_path}: {e}")


def get_video_info(filepath):
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration,size,bit_rate',
        '-show_entries', 'stream=width,height,r_frame_rate,codec_name',
        '-of', 'default=noprint_wrappers=1', filepath
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    info = {
        'duration': 0.0,
        'width': 'N/A',
        'height': 'N/A',
        'fps': 'N/A',
        'codec': 'N/A',
        'bitrate': 'N/A',
        'audio_codec': 'aac',
        'size': f"{round(os.path.getsize(filepath) / (1024 * 1024), 2)} MB"
    }

    for line in result.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            if key == 'duration':
                try: info['duration'] = float(value)
                except ValueError: pass
            elif key == 'width': info['width'] = value
            elif key == 'height': info['height'] = value
            elif key == 'codec_name' and info['codec'] == 'N/A': info['codec'] = value
            elif key == 'r_frame_rate':
                if '/' in value:
                    num, den = value.split('/')
                    if float(den) > 0:
                        info['fps'] = str(round(float(num) / float(den), 2))
                else:
                    info['fps'] = value

    return info


def process_video_background(input_path, output_path, filename, duration, preset_mode='max', normalize_audio=True):
    progress_tracker[filename] = 0

    if preset_mode == 'fast':
        ffmpeg_preset = 'ultrafast'
        crf_val = '22'
    else:
        ffmpeg_preset = 'slow'
        crf_val = '16'

    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-c:v', 'libx264', '-preset', ffmpeg_preset, '-crf', crf_val,
        '-pix_fmt', 'yuv420p'
    ]

    if normalize_audio:
        cmd.extend(['-af', 'loudnorm=I=-16:LRA=11:TP=-1.5'])

    cmd.extend([
        '-c:a', 'aac', '-b:a', '320k',
        '-movflags', '+faststart',
        output_path
    ])

    process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
    time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

    for line in process.stderr:
        match = time_pattern.search(line)
        if match and duration > 0:
            hours, minutes, seconds = map(float, match.groups())
            current_time = (hours * 3600) + (minutes * 60) + seconds
            percent = int((current_time / duration) * 100)
            progress_tracker[filename] = min(percent, 99)

    process.wait()
    progress_tracker[filename] = 100


@app.route('/')
def index():
    cleanup_old_files()
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    cleanup_old_files()
    if 'video' not in request.files:
        return "No file uploaded", 400

    file = request.files['video']
    if file.filename == '':
        return "No selected file", 400

    input_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(input_path)

    info = get_video_info(input_path)
    info['filename'] = file.filename

    return render_template('result.html', info=info)


@app.route('/start_optimize', methods=['POST'])
def start_optimize():
    data = request.get_json()
    filename = data.get('filename')
    preset_mode = data.get('preset', 'max')
    normalize_audio = data.get('normalize_audio', True)

    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    input_path = os.path.join(UPLOAD_FOLDER, filename)
    output_path = os.path.join(OUTPUT_FOLDER, filename)

    info = get_video_info(input_path)
    duration = info['duration']

    thread = threading.Thread(
        target=process_video_background,
        args=(input_path, output_path, filename, duration, preset_mode, normalize_audio)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started', 'filename': filename})


@app.route('/progress/<filename>')
def get_progress(filename):
    percent = progress_tracker.get(filename, 0)
    return jsonify({'percent': percent})


@app.route('/download_page/<filename>')
def download_page(filename):
    return render_template('download.html', filename=filename)


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


if __name__ == '__main__':
    cleanup_old_files()
    app.run(debug=True, host='0.0.0.0', port=80)