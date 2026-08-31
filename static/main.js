document.addEventListener("DOMContentLoaded", () => {
    const videoInput = document.getElementById("video-input");
    const dropzone = document.getElementById("dropzone");
    const filePreview = document.getElementById("file-preview");
    const fileNameText = document.getElementById("file-name-text");
    const changeVideoBtn = document.getElementById("change-video-btn");
    const optimizerForm = document.getElementById("optimizer-form");
    const submitBtn = document.getElementById("submit-btn");

    const progressBox = document.getElementById("progress-box");
    const progressStatus = document.getElementById("progress-status");
    const progressFill = document.getElementById("progress-fill");

    const downscaleModal = document.getElementById("downscale-modal");
    const cancelModalBtn = document.getElementById("cancel-modal-btn");
    const localProcessingView = document.getElementById("local-processing-view");

    // File Selection via Dropzone
    dropzone.addEventListener("click", () => videoInput.click());

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "#b57edc";
        dropzone.style.background = "rgba(181, 126, 220, 0.15)";
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.style.borderColor = "rgba(181, 126, 220, 0.5)";
        dropzone.style.background = "rgba(28, 22, 40, 0.4)";
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "rgba(181, 126, 220, 0.5)";
        dropzone.style.background = "rgba(28, 22, 40, 0.4)";
        if (e.dataTransfer.files.length > 0) {
            videoInput.files = e.dataTransfer.files;
            handleFileSelection();
        }
    });

    videoInput.addEventListener("change", handleFileSelection);

    changeVideoBtn.addEventListener("click", () => {
        videoInput.value = "";
        filePreview.style.display = "none";
        dropzone.style.display = "block";
    });

    function handleFileSelection() {
        if (videoInput.files && videoInput.files[0]) {
            const file = videoInput.files[0];
            fileNameText.textContent = file.name;
            dropzone.style.display = "none";
            filePreview.style.display = "flex";

            // Inspect resolution; show downscaler modal for high-res inputs
            checkVideoResolution(file);
        }
    }

    function checkVideoResolution(file) {
        const video = document.createElement("video");
        video.preload = "metadata";
        video.src = URL.createObjectURL(file);
        video.onloadedmetadata = () => {
            URL.revokeObjectURL(video.src);
            if (video.videoWidth > 1920 || video.videoHeight > 1080) {
                downscaleModal.style.display = "flex";
            }
        };
    }

    if (cancelModalBtn) {
        cancelModalBtn.addEventListener("click", () => {
            downscaleModal.style.display = "none";
        });
    }

    // Radio option visual selection logic
    const optionCards = document.querySelectorAll(".option-card");
    optionCards.forEach((card) => {
        const radio = card.querySelector('input[type="radio"]');
        if (radio) {
            card.addEventListener("click", () => {
                optionCards.forEach((c) => c.classList.remove("selected"));
                card.classList.add("selected");
                radio.checked = true;
            });
        }
    });

    // Form Submission with Upload Progress Tracking
    optimizerForm.addEventListener("submit", (e) => {
        if (!videoInput.files || videoInput.files.length === 0) {
            return; // Let standard form validation alert user
        }

        e.preventDefault();

        // UI transitions to processing state
        submitBtn.disabled = true;
        downscaleModal.style.display = "none";
        progressBox.style.display = "block";

        const formData = new FormData(optimizerForm);
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener("progress", (event) => {
            if (event.lengthComputable) {
                const percentComplete = Math.round((event.loaded / event.total) * 100);
                progressFill.style.width = percentComplete + "%";
                progressStatus.textContent = `Uploading Video... ${percentComplete}%`;

                if (percentComplete === 100) {
                    // Show cloud rendering spinner view once upload completes
                    optimizerForm.style.display = "none";
                    progressBox.style.display = "none";
                    localProcessingView.style.display = "block";
                }
            }
        });

        xhr.onload = function () {
            if (xhr.status === 200) {
                // Replace page content with server response (contains download link)
                document.open();
                document.write(xhr.responseText);
                document.close();
            } else {
                alert("An error occurred during video processing. Please try again.");
                submitBtn.disabled = false;
                progressBox.style.display = "none";
            }
        };

        xhr.onerror = function () {
            alert("Network error occurred during upload.");
            submitBtn.disabled = false;
            progressBox.style.display = "none";
        };

        xhr.open("POST", optimizerForm.action, true);
        xhr.send(formData);
    });
});
