document.addEventListener("DOMContentLoaded", function () {
    let selectedFile = null;

    const dropzone = document.getElementById('dropzone');
    const videoInput = document.getElementById('video-input');
    const changeBtn = document.getElementById('change-video-btn');
    const modal = document.getElementById('downscale-modal');
    const cancelModalBtn = document.getElementById('cancel-modal-btn');
    const optGpu = document.getElementById('opt-gpu');
    const optCpu = document.getElementById('opt-cpu');
    const tiktokCard = document.getElementById('tiktok-card');
    const tiktokInput = document.getElementById('optimize_tiktok_input');
    const form = document.getElementById('optimizer-form');

    // Trigger File Input safely on Dropzone / Change clicks
    if (dropzone) {
        dropzone.addEventListener('click', () => videoInput.click());
    }
    if (changeBtn) {
        changeBtn.addEventListener('click', () => videoInput.click());
    }

    // Handle Video Input Selection
    if (videoInput) {
        videoInput.addEventListener('change', function () {
            if (this.files && this.files[0]) {
                selectedFile = this.files[0];
                document.getElementById('dropzone').style.display = 'none';
                document.getElementById('file-preview').style.display = 'flex';
                document.getElementById('file-name-text').innerText = selectedFile.name;

                document.getElementById('step-node-2').classList.add('active');
                document.getElementById('step-badge-1').innerText = '✓';

                const videoElem = document.createElement('video');
                videoElem.preload = 'metadata';
                videoElem.src = URL.createObjectURL(selectedFile);

                videoElem.onloadedmetadata = function () {
                    URL.revokeObjectURL(videoElem.src);
                    if (videoElem.videoHeight > 1080 || videoElem.videoWidth > 1920) {
                        modal.style.display = 'flex';
                    }
                };
            }
        });
    }

    // Modal Operations
    if (cancelModalBtn) {
        cancelModalBtn.addEventListener('click', () => { modal.style.display = 'none'; });
    }

    if (optGpu) optGpu.addEventListener('click', startLocalEncoding);
    if (optCpu) optCpu.addEventListener('click', startLocalEncoding);

    // Radio button UI sync
    document.querySelectorAll('.option-card input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', function () {
            document.querySelectorAll('.option-card').forEach(card => {
                if (!card.querySelector('input[type="checkbox"]')) {
                    card.classList.remove('selected');
                }
            });
            this.closest('.option-card').classList.add('selected');
        });
    });

    // TikTok Checkbox Sync
    if (tiktokCard) {
        tiktokCard.addEventListener('click', function (e) {
            if (e.target !== tiktokInput) {
                tiktokInput.checked = !tiktokInput.checked;
            }
            if (tiktokInput.checked) {
                tiktokCard.classList.add('selected');
            } else {
                tiktokCard.classList.remove('selected');
            }
        });
    }

    // Hybrid Local Encoding Handler
    async function startLocalEncoding() {
        modal.style.display = 'none';
        document.getElementById('optimizer-form').style.display = 'none';
        document.getElementById('local-processing-view').style.display = 'block';

        const supportsWebCodecs = typeof window.VideoEncoder === 'function' && typeof window.VideoDecoder === 'function';
        if (supportsWebCodecs) {
            try {
                await runWebCodecsEncoding();
                return;
            } catch (err) {
                console.warn("WebCodecs GPU pipeline bypassed. Switching to WASM...", err);
            }
        }

        try {
            await runWasmEncoding();
            return;
        } catch (err) {
            console.warn("WASM bypassed. Switching to Server Encoding...", err);
        }

        document.getElementById('local-processing-view').style.display = 'none';
        document.getElementById('optimizer-form').style.display = 'block';
        form.submit();
    }

    // WebAssembly Engine
    async function runWasmEncoding() {
        const { createFFmpeg, fetchFile } = FFmpeg;
        const ffmpegWasm = createFFmpeg({ log: true });
        const startTime = Date.now();

        if (!ffmpegWasm.isLoaded()) {
            await ffmpegWasm.load();
        }

        ffmpegWasm.setProgress(({ ratio }) => {
            const percent = Math.min(Math.round(ratio * 100), 100);
            document.getElementById('local-progress-fill').style.width = percent + '%';
            document.getElementById('local-progress-percent').innerText = percent + '%';

            const elapsedSec = (Date.now() - startTime) / 1000;
            if (ratio > 0.02) {
                const totalSec = elapsedSec / ratio;
                const remainingSec = Math.round(totalSec - elapsedSec);
                document.getElementById('local-time-left').innerText = `About ${remainingSec} sec left`;
            }
        });

        ffmpegWasm.FS('writeFile', 'input.mp4', await fetchFile(selectedFile));

        const isTikTok = tiktokInput.checked;
        let args = ['-i', 'input.mp4', '-vf', 'scale=-2:1080', '-c:v', 'libx264', '-preset', 'ultrafast'];
        if (isTikTok) {
            args.push('-maxrate', '8M', '-bufsize', '16M', '-crf', '23');
        } else {
            args.push('-crf', '20');
        }
        args.push('output.mp4');

        await ffmpegWasm.run(...args);

        const data = ffmpegWasm.FS('readFile', 'output.mp4');
        const blob = new Blob([data.buffer], { type: 'video/mp4' });
        const downloadUrl = URL.createObjectURL(blob);

        renderCompletionView(downloadUrl, "Processed entirely on this device using client-side CPU acceleration.");
    }

    // WebCodecs Engine
    async function runWebCodecsEncoding() {
        document.getElementById('local-time-left').innerText = "Initializing GPU Engine...";

        const fileBuffer = await selectedFile.arrayBuffer();
        fileBuffer.fileStart = 0;

        const muxer = new Mp4Muxer.Muxer({
            target: new Mp4Muxer.ArrayBufferTarget(),
            video: { codec: 'avc', width: 1920, height: 1080 },
            fastStart: 'in-memory'
        });

        const encoder = new VideoEncoder({
            output: (chunk, metadata) => muxer.addVideoChunk(chunk, metadata),
            error: (e) => console.error("GPU Encoder error:", e)
        });

        await encoder.configure({
            codec: 'avc1.4d4028',
            width: 1920,
            height: 1080,
            bitrate: 8_000_000,
            framerate: 60,
            hardwareAcceleration: 'prefer-hardware'
        });

        const canvas = document.createElement('canvas');
        canvas.width = 1920;
        canvas.height = 1080;
        const ctx = canvas.getContext('2d');

        let frameIndex = 0;
        let processedFrames = 0;

        const decoder = new VideoDecoder({
            output: async (frame) => {
                ctx.drawImage(frame, 0, 0, 1920, 1080);
                const scaledFrame = new VideoFrame(canvas, {
                    timestamp: frame.timestamp,
                    duration: frame.duration
                });

                const keyFrame = (frameIndex % 60 === 0);
                encoder.encode(scaledFrame, { keyFrame: keyFrame });

                scaledFrame.close();
                frame.close();
                frameIndex++;

                processedFrames++;
                const progress = Math.min(Math.round((processedFrames / 1800) * 100), 99);
                document.getElementById('local-progress-fill').style.width = progress + '%';
                document.getElementById('local-progress-percent').innerText = progress + '%';
                document.getElementById('local-time-left').innerText = "Encoding via GPU WebCodecs Pipeline...";
            },
            error: (e) => console.error("GPU Decoder error:", e)
        });

        const mp4boxfile = MP4Box.createFile();
        mp4boxfile.onReady = function (info) {
            const videoTrack = info.videoTracks[0];
            decoder.configure({
                codec: videoTrack.codec,
                codedWidth: videoTrack.video_dimensions.width,
                codedHeight: videoTrack.video_dimensions.height,
                description: mp4boxfile.getTrackById(videoTrack.id).description
            });
            mp4boxfile.setExtractionOptions(videoTrack.id, null, { nbSamples: 100 });
            mp4boxfile.start();
        };

        mp4boxfile.onSamples = function (track_id, ref, samples) {
            for (let sample of samples) {
                const chunk = new EncodedVideoChunk({
                    type: sample.is_sync ? 'key' : 'delta',
                    timestamp: (sample.cts * 1000000) / sample.timescale,
                    duration: (sample.duration * 1000000) / sample.timescale,
                    data: sample.data
                });
                decoder.decode(chunk);
            }
        };

        mp4boxfile.appendBuffer(fileBuffer);
        mp4boxfile.flush();

        await decoder.flush();
        await encoder.flush();
        muxer.finalize();

        const { buffer } = muxer.target;
        const blob = new Blob([buffer], { type: 'video/mp4' });
        const downloadUrl = URL.createObjectURL(blob);

        renderCompletionView(downloadUrl, "Processed instantly via GPU WebCodecs hardware engine.");
    }

    function renderCompletionView(downloadUrl, messageText) {
        document.getElementById('local-processing-view').innerHTML = `
            <div style="font-size: 50px;">⚡</div>
            <div class="status-tag" style="margin-top: 10px;">RENDER COMPLETE</div>
            <h2 class="render-title">Your video is ready</h2>
            <p class="render-sub">${messageText}</p>
            <a class="download-btn" href="${downloadUrl}" download="optimized_${selectedFile.name}">Download Video</a>
        `;

        document.getElementById('step-node-3').classList.add('active');
        document.getElementById('step-badge-2').innerText = '✓';
    }

    // Ajax Form Submission
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();

            if (!videoInput.files.length) return;

            const formData = new FormData(form);
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/optimize', true);

            const progressBox = document.getElementById('progress-box');
            const progressFill = document.getElementById('progress-fill');
            const progressStatus = document.getElementById('progress-status');
            const submitBtn = document.getElementById('submit-btn');

            xhr.upload.onprogress = function (e) {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 90);
                    progressFill.style.width = percent + '%';
                    progressStatus.innerText = 'Uploading Video... ' + percent + '%';
                }
            };

            xhr.upload.onload = function () {
                progressFill.style.width = '95%';
                progressStatus.innerText = 'Encoding & Optimizing Video... Please Wait';
            };

            xhr.onload = function () {
                if (xhr.status === 200) {
                    progressFill.style.width = '100%';
                    progressStatus.innerText = 'Processing Complete!';

                    document.open();
                    document.write(xhr.responseText);
                    document.close();
                } else {
                    alert('Optimization failed. Please try again.');
                    submitBtn.disabled = false;
                }
            };

            progressBox.style.display = 'block';
            submitBtn.disabled = true;
            xhr.send(formData);
        });
    }
});
