document.addEventListener("DOMContentLoaded", () => {
    const videoInput = document.getElementById("video-input");
    const dropzone = document.getElementById("dropzone");
    const filePreview = document.getElementById("file-preview");
    const fileNameText = document.getElementById("file-name-text");
    const changeVideoBtn = document.getElementById("change-video-btn");
    const optimizerForm = document.getElementById("optimizer-form");
    const submitBtn = document.getElementById("submit-btn");

    const downscaleModal = document.getElementById("downscale-modal");
    const cancelModalBtn = document.getElementById("cancel-modal-btn");
    const localProcessingView = document.getElementById("local-processing-view");

    // Elements in local processing view
    const localProgressFill = document.getElementById("local-progress-fill");
    const localProgressPercent = document.getElementById("local-progress-percent");
    const localTimeLeft = document.getElementById("local-time-left");

    // Step Node indicators
    const stepNode1 = document.getElementById("step-node-1");
    const stepNode2 = document.getElementById("step-node-2");
    const stepNode3 = document.getElementById("step-node-3");

    // Dropzone logic
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
        if (stepNode2) stepNode2.classList.remove("active");
    });

    function handleFileSelection() {
        if (videoInput.files && videoInput.files[0]) {
            const file = videoInput.files[0];
            fileNameText.textContent = file.name;
            dropzone.style.display = "none";
            filePreview.style.display = "flex";

            if (stepNode2) stepNode2.classList.add("active");

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

    // Radio card visual selector
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

    // Handle AJAX Submission
    optimizerForm.addEventListener("submit", (e) => {
        if (!videoInput.files || videoInput.files.length === 0) {
            return;
        }

        e.preventDefault();

        // 1. Hide modal and form, show loading screen
        downscaleModal.style.display = "none";
        optimizerForm.style.display = "none";
        localProcessingView.style.display = "block";

        // Reset status visuals
        localProgressFill.style.width = "0%";
        localProgressPercent.textContent = "0%";
        localTimeLeft.textContent = "Uploading to server...";

        const formData = new FormData(optimizerForm);
        const xhr = new XMLHttpRequest();

        // 2. Track live upload progress
        xhr.upload.addEventListener("progress", (event) => {
            if (event.lengthComputable) {
                const percentComplete = Math.round((event.loaded / event.total) * 100);
                localProgressFill.style.width = percentComplete + "%";
                localProgressPercent.textContent = percentComplete + "%";

                if (percentComplete < 100) {
                    localTimeLeft.textContent = `Uploading Video... ${percentComplete}%`;
                } else {
                    localTimeLeft.textContent = "Encoding on Cloud Server... Please wait";
                }
            }
        });

        // 3. Process completed server response
        xhr.onload = function () {
            if (xhr.status === 200) {
                try {
                    const data = JSON.parse(xhr.responseText);

                    if (data.success) {
                        // Hide loading view
                        localProcessingView.style.display = "none";

                        // Activate Step 3 Badge
                        if (stepNode3) stepNode3.classList.add("active");

                        // Dynamically create or update download card
                        let downloadSection = document.getElementById("download-section");
                        if (!downloadSection) {
                            downloadSection = document.createElement("div");
                            downloadSection.id = "download-section";
                            downloadSection.className = "download-card";
                            document.querySelector(".content-card").appendChild(downloadSection);
                        }

                        downloadSection.innerHTML = `
                            <h3 style="margin: 0; color: #b57edc;">Optimization Complete!</h3>
                            <p style="font-size: 13px; color: #aaa; margin: 5px 0 15px 0;">Your video file is optimized and ready.</p>
                            <a class="download-btn" href="${data.download_url}">Download Optimized Video</a>
                        `;
                        downloadSection.style.display = "block";

                    } else {
                        alert("Processing Error: " + (data.error || "Failed on server"));
                        resetUI();
                    }
                } catch (err) {
                    alert("Error parsing response from server.");
                    resetUI();
                }
            } else {
                alert("Server error occurred (" + xhr.status + "). Please try again.");
                resetUI();
            }
        };

        xhr.onerror = function () {
            alert("Network error during upload.");
            resetUI();
        };

        xhr.open("POST", optimizerForm.action, true);
        xhr.send(formData);
    });

    function resetUI() {
        localProcessingView.style.display = "none";
        optimizerForm.style.display = "block";
        if (submitBtn) submitBtn.disabled = false;
    }
});
