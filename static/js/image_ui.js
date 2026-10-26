// Image Cryptography Suite UI Controller (Image XOR, Steganography, PicIt)

document.addEventListener("DOMContentLoaded", () => {
    // ==================== 1. IMAGE XOR CONTROLLER ====================
    let xorFile = null;
    let xorFileBuffer = null;
    let xorFilePromise = null;
    let xorResultBlob = null;

    const xorDropzone = document.getElementById("ixor-dropzone");
    const xorFileInput = document.getElementById("ixor-file-input");
    const xorFileCard = document.getElementById("ixor-file-card");
    const xorFileName = document.getElementById("ixor-file-name");
    const xorRemoveBtn = document.getElementById("ixor-remove-file");

    const xorKeyInput = document.getElementById("ixor-key");
    const xorEncryptBtn = document.getElementById("ixor-encrypt-btn");
    const xorDecryptBtn = document.getElementById("ixor-decrypt-btn");

    const xorProgressBox = document.getElementById("ixor-progress");
    const xorProgressFill = document.getElementById("ixor-progress-fill");
    const xorProgressText = document.getElementById("ixor-progress-text");
    const xorProgressSub = document.getElementById("ixor-progress-sub");

    const xorResultCard = document.getElementById("ixor-result-card");
    const xorPreviewImg = document.getElementById("ixor-preview-img");
    const xorDownloadBtn = document.getElementById("ixor-download-btn");

    function updateXorProgress(percent, current, total) {
        if (!xorProgressBox) return;
        xorProgressBox.classList.add("visible");
        if (xorProgressFill) xorProgressFill.style.width = `${percent}%`;
        if (xorProgressText) xorProgressText.textContent = `${percent}%`;
        if (xorProgressSub) xorProgressSub.textContent = `Processing image pixels (${percent}%)...`;
    }

    function hideXorProgress() {
        if (xorProgressBox) xorProgressBox.classList.remove("visible");
    }

    // Local robust byte reader fallback
    const readAsBytes = async (file) => {
        if (!file) throw new Error("No file provided.");
        if (typeof window.readFileAsUint8Array === "function") {
            try {
                return await window.readFileAsUint8Array(file);
            } catch (e) {
                console.warn("window.readFileAsUint8Array error, trying native arrayBuffer:", e);
            }
        }
        if (typeof file.arrayBuffer === "function") {
            try {
                const ab = await file.arrayBuffer();
                return new Uint8Array(ab);
            } catch (e) {
                console.warn("file.arrayBuffer error, trying FileReader:", e);
            }
        }
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(new Uint8Array(reader.result));
            reader.onerror = () => reject(reader.error || new Error("Failed to read file"));
            reader.readAsArrayBuffer(file);
        });
    };

    function setXorFile(file) {
        if (!file) return;
        xorFile = file;
        xorFileName.textContent = file.name;
        xorFileCard.classList.add("visible");
        xorDropzone.style.display = "none";
        xorResultCard.classList.remove("visible");
        if (xorDropzone) xorDropzone.classList.remove("field-highlight-error");

        // Buffer bytes into memory immediately (protects mobile transient permissions, ready for PC)
        xorFileBuffer = null;
        xorFilePromise = readAsBytes(file)
            .then(buf => {
                xorFileBuffer = buf;
                return buf;
            })
            .catch(err => {
                console.warn("XOR buffering delayed:", err);
                return null;
            });
    }

    if (xorDropzone && xorFileInput) {
        xorDropzone.addEventListener("click", () => {
            xorFileInput.value = "";
            xorFileInput.click();
        });
        xorDropzone.addEventListener("dragover", (e) => { e.preventDefault(); xorDropzone.classList.add("dragover"); });
        xorDropzone.addEventListener("dragleave", () => xorDropzone.classList.remove("dragover"));
        xorDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            xorDropzone.classList.remove("dragover");
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
                setXorFile(e.dataTransfer.files[0]);
            }
        });
    }

    if (xorFileInput) {
        xorFileInput.addEventListener("click", (e) => {
            e.target.value = "";
        });
        xorFileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) setXorFile(e.target.files[0]);
        });
    }

    if (xorRemoveBtn) {
        xorRemoveBtn.addEventListener("click", () => {
            xorFile = null;
            xorFileBuffer = null;
            xorFilePromise = null;
            if (xorFileInput) xorFileInput.value = "";
            xorFileCard.classList.remove("visible");
            xorDropzone.style.display = "block";
            xorResultCard.classList.remove("visible");
            hideXorProgress();
        });
    }

    async function handleXorOperation(op) {
        if (!xorFile) {
            if (window.highlightField) window.highlightField("ixor-dropzone");
            return showToast("Please select an image file.", "error");
        }
        const key = xorKeyInput.value.trim();
        if (!key) {
            if (window.highlightField) window.highlightField("ixor-key");
            return showToast("Please provide an encryption key.", "error");
        }

        try {
            xorEncryptBtn.disabled = true;
            xorDecryptBtn.disabled = true;
            hideXorProgress();
            updateXorProgress(15, 1, 4);
            showToast(`${op === 'encrypt' ? 'Encrypting' : 'Decrypting'} image pixels...`, "info");

            let buffer = xorFileBuffer;
            if (!buffer && xorFilePromise) {
                try {
                    buffer = await xorFilePromise;
                } catch (e) {
                    console.warn("Cached promise failed, re-reading:", e);
                }
            }
            if (!buffer && xorFile) {
                try {
                    buffer = await readAsBytes(xorFile);
                    xorFileBuffer = buffer;
                } catch (readErr) {
                    if (window.highlightField) window.highlightField("ixor-dropzone");
                    throw new Error("The image file could not be read. Please tap the file area to select it again.");
                }
            }

            if (!buffer || buffer.byteLength === 0) {
                throw new Error("Image buffer is empty or could not be loaded.");
            }

            const resultData = await window.cryptoEngine.processImageXor({
                imgData: buffer,
                key: key,
                operation: op,
                onProgress: ({ percent, currentBlock, totalBlocks }) => {
                    updateXorProgress(percent, currentBlock, totalBlocks);
                }
            });

            updateXorProgress(100, 4, 4);
            xorResultBlob = new Blob([resultData], { type: "image/png" });
            xorPreviewImg.src = URL.createObjectURL(xorResultBlob);
            xorResultCard.classList.add("visible");

            showToast(`Image ${op === 'encrypt' ? 'encrypted' : 'decrypted'} successfully!`, "success");
        } catch (err) {
            console.error(err);
            showToast(`Image XOR failed: ${err.message}`, "error");
        } finally {
            xorEncryptBtn.disabled = false;
            xorDecryptBtn.disabled = false;
            setTimeout(() => hideXorProgress(), 800);
        }
    }

    if (xorEncryptBtn) xorEncryptBtn.addEventListener("click", () => handleXorOperation("encrypt"));
    if (xorDecryptBtn) xorDecryptBtn.addEventListener("click", () => handleXorOperation("decrypt"));
    const xorPreviewBtn = document.getElementById("ixor-preview-btn");
    if (xorPreviewBtn) {
        xorPreviewBtn.addEventListener("click", () => {
            if (xorPreviewImg && xorPreviewImg.src && window.openImagePreviewModal) {
                window.openImagePreviewModal(xorPreviewImg.src, "Image XOR Processed Image", "Bitwise XOR & Pixel Coordinate Scrambler Output");
            }
        });
    }
    if (xorPreviewImg) {
        xorPreviewImg.addEventListener("click", () => {
            if (xorPreviewImg.src && window.openImagePreviewModal) {
                window.openImagePreviewModal(xorPreviewImg.src, "Image XOR Processed Image", "Bitwise XOR & Pixel Coordinate Scrambler Output");
            }
        });
    }

    if (xorDownloadBtn) {
        xorDownloadBtn.addEventListener("click", () => {
            if (xorResultBlob) {
                const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                if (window.promptAndDownloadBlob) {
                    window.promptAndDownloadBlob(xorResultBlob, `image_xor_${ts}.png`, ".png");
                } else {
                    downloadBlob(xorResultBlob, `image_xor_${ts}.png`, "image/png");
                }
            }
        });
    }

    // ==================== 2. STEGANOGRAPHY CONTROLLER ====================
    let stegFile = null;
    let stegFileBuffer = null;
    let stegFilePromise = null;
    let stegResultBlob = null;

    const stegDropzone = document.getElementById("steg-dropzone");
    const stegFileInput = document.getElementById("steg-file-input");
    const stegFileCard = document.getElementById("steg-file-card");
    const stegFileName = document.getElementById("steg-file-name");
    const stegRemoveBtn = document.getElementById("steg-remove-file");

    const stegKeyInput = document.getElementById("steg-key");
    const stegMsgInput = document.getElementById("steg-message");
    const stegProtectCheck = document.getElementById("steg-protect-toggle");
    const stegCipherSelect = document.getElementById("steg-cipher-select");
    const stegVigenereOptions = document.getElementById("steg-vigenere-options");
    const stegVigenerePlusCheck = document.getElementById("steg-vigenere-plus-check");

    const stegProgressBox = document.getElementById("steg-progress");
    const stegProgressFill = document.getElementById("steg-progress-fill");
    const stegProgressText = document.getElementById("steg-progress-text");
    const stegProgressSub = document.getElementById("steg-progress-sub");

    const stegHideBtn = document.getElementById("steg-hide-btn");
    const stegExtractBtn = document.getElementById("steg-extract-btn");

    const stegResultCard = document.getElementById("steg-result-card");
    const stegBeforeImg = document.getElementById("steg-before-img");
    const stegPreviewImg = document.getElementById("steg-preview-img");
    const stegPreviewBtn = document.getElementById("steg-preview-btn");
    const stegDownloadBtn = document.getElementById("steg-download-btn");
    const stegExtractedBox = document.getElementById("steg-extracted-box");
    const stegExtractedText = document.getElementById("steg-extracted-text");
    const stegCopyExtractedBtn = document.getElementById("steg-copy-extracted-btn");
    const stegSaveExtractedBtn = document.getElementById("steg-save-extracted-btn");

    function handleStegCipherChange() {
        const cipher = stegCipherSelect ? stegCipherSelect.value : "vigenere";
        if (stegVigenereOptions) {
            stegVigenereOptions.style.display = (cipher === "vigenere") ? "block" : "none";
        }
    }
    if (stegCipherSelect) {
        stegCipherSelect.addEventListener("change", handleStegCipherChange);
    }
    handleStegCipherChange();

    function updateStegProgress(percent, current, total, text = "Processing steganography...") {
        if (!stegProgressBox) return;
        stegProgressBox.classList.add("visible");
        if (stegProgressFill) stegProgressFill.style.width = `${percent}%`;
        if (stegProgressText) stegProgressText.textContent = `${percent}%`;
        if (stegProgressSub) stegProgressSub.textContent = `${text} (${percent}%)`;
    }

    function hideStegProgress() {
        if (stegProgressBox) stegProgressBox.classList.remove("visible");
    }

    function setStegFile(file) {
        if (!file) return;
        stegFile = file;
        stegFileName.textContent = file.name;
        stegFileCard.classList.add("visible");
        stegDropzone.style.display = "none";
        stegResultCard.classList.remove("visible");
        stegExtractedBox.style.display = "none";
        if (stegDropzone) stegDropzone.classList.remove("field-highlight-error");

        // Immediately buffer bytes into memory while Android/mobile permission lease is fresh
        stegFileBuffer = null;
        stegFilePromise = readAsBytes(file)
            .then(buf => {
                stegFileBuffer = buf;
                if (stegBeforeImg) {
                    const b = new Blob([buf], { type: file.type || "image/png" });
                    stegBeforeImg.src = URL.createObjectURL(b);
                }
                return buf;
            })
            .catch(err => {
                console.warn("Steganos buffering deferred or failed:", err);
                return null;
            });
    }

    if (stegDropzone && stegFileInput) {
        stegDropzone.addEventListener("click", () => {
            stegFileInput.value = "";
            stegFileInput.click();
        });
        stegFileInput.addEventListener("click", (e) => {
            e.target.value = "";
        });
        stegDropzone.addEventListener("dragover", (e) => { e.preventDefault(); stegDropzone.classList.add("dragover"); });
        stegDropzone.addEventListener("dragleave", () => stegDropzone.classList.remove("dragover"));
        stegDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            stegDropzone.classList.remove("dragover");
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
                setStegFile(e.dataTransfer.files[0]);
            }
        });
    }

    if (stegFileInput) {
        stegFileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) setStegFile(e.target.files[0]);
        });
    }

    if (stegRemoveBtn) {
        stegRemoveBtn.addEventListener("click", () => {
            stegFile = null;
            stegFileBuffer = null;
            stegFilePromise = null;
            if (stegFileInput) stegFileInput.value = "";
            stegFileCard.classList.remove("visible");
            stegDropzone.style.display = "block";
            stegResultCard.classList.remove("visible");
            stegExtractedBox.style.display = "none";
            if (stegBeforeImg) stegBeforeImg.src = "";
            hideStegProgress();
        });
    }

    // Steganography Protection Toggle
    function handleStegProtectChange() {
        if (!stegKeyInput) return;
        const isProtected = stegProtectCheck ? stegProtectCheck.checked : false;
        if (isProtected) {
            stegKeyInput.placeholder = "Password required to extract hidden message";
        } else {
            stegKeyInput.placeholder = "Key (Optional: leave blank for automatic carrier key)";
        }
    }
    if (stegProtectCheck) {
        stegProtectCheck.addEventListener("change", handleStegProtectChange);
        handleStegProtectChange();
    }

    // Hide message into image
    if (stegHideBtn) {
        stegHideBtn.addEventListener("click", async () => {
            if (!stegFile) {
                if (window.highlightField) window.highlightField("steg-dropzone");
                return showToast("Select a cover image first.", "error");
            }
            const message = stegMsgInput.value.trim();
            if (!message) {
                if (window.highlightField) window.highlightField("steg-message");
                return showToast("Enter a secret message to hide.", "error");
            }
            const key = stegKeyInput.value.trim();
            const isProtected = stegProtectCheck ? stegProtectCheck.checked : false;

            if (isProtected && !key) {
                if (window.highlightField) window.highlightField("steg-key");
                return showToast("Please enter a password for password-protected steganography.", "error");
            }

            try {
                stegHideBtn.disabled = true;
                stegExtractBtn.disabled = true;
                hideStegProgress();
                updateStegProgress(10, 1, 5, "Embedding secret message into pixels...");
                showToast("Embedding secret message via LSB Steganography...", "info");

                let buffer = stegFileBuffer;
                if (!buffer && stegFilePromise) {
                    try {
                        buffer = await stegFilePromise;
                    } catch (e) {
                        // Fallback below
                    }
                }
                if (!buffer && stegFile) {
                    try {
                        buffer = await readAsBytes(stegFile);
                        stegFileBuffer = buffer;
                    } catch (readErr) {
                        if (window.highlightField) window.highlightField("steg-dropzone");
                        throw new Error("The image file could not be read. Please tap the file area to select it again.");
                    }
                }

                if (!buffer || buffer.byteLength === 0) {
                    throw new Error("Cover image buffer is empty or could not be loaded.");
                }

                let cipher = stegCipherSelect ? stegCipherSelect.value : "vigenere";
                if (cipher === "vigenere" && stegVigenerePlusCheck && stegVigenerePlusCheck.checked) {
                    cipher = "vigenere_plus";
                }

                const resultBytes = await window.cryptoEngine.steganosHide({
                    imgData: buffer,
                    message: message,
                    key: key,
                    passwordProtected: isProtected,
                    textCipher: cipher,
                    onProgress: ({ percent, currentBlock, totalBlocks }) => {
                        updateStegProgress(percent, currentBlock, totalBlocks, "Embedding message into pixels...");
                    }
                });

                updateStegProgress(100, 5, 5, "Complete!");
                stegResultBlob = new Blob([resultBytes], { type: "image/png" });
                stegPreviewImg.src = URL.createObjectURL(stegResultBlob);
                stegResultCard.classList.add("visible");
                stegExtractedBox.style.display = "none";

                showToast("Message hidden in image successfully!", "success");
            } catch (err) {
                console.error(err);
                showToast(`Steganography failed: ${err.message}`, "error");
            } finally {
                stegHideBtn.disabled = false;
                stegExtractBtn.disabled = false;
                setTimeout(() => hideStegProgress(), 800);
            }
        });
    }

    // Extract message from image
    if (stegExtractBtn) {
        stegExtractBtn.addEventListener("click", async () => {
            if (!stegFile) {
                if (window.highlightField) window.highlightField("steg-dropzone");
                return showToast("Select an image to extract from.", "error");
            }
            const key = stegKeyInput.value.trim();

            let overrideCipher = stegCipherSelect ? stegCipherSelect.value : null;
            if (overrideCipher === "vigenere" && stegVigenerePlusCheck && stegVigenerePlusCheck.checked) {
                overrideCipher = "vigenere_plus";
            }

            try {
                stegHideBtn.disabled = true;
                stegExtractBtn.disabled = true;
                hideStegProgress();
                updateStegProgress(10, 1, 5, "Extracting secret message from image...");
                showToast("Extracting secret message from image...", "info");

                let buffer = stegFileBuffer;
                if (!buffer && stegFilePromise) {
                    try {
                        buffer = await stegFilePromise;
                    } catch (e) {
                        // Fallback below
                    }
                }
                if (!buffer && stegFile) {
                    try {
                        buffer = await readAsBytes(stegFile);
                        stegFileBuffer = buffer;
                    } catch (readErr) {
                        if (window.highlightField) window.highlightField("steg-dropzone");
                        throw new Error("The image file could not be read. Please tap the file area to select it again.");
                    }
                }

                if (!buffer || buffer.byteLength === 0) {
                    throw new Error("Steganography image buffer is empty or could not be loaded.");
                }

                const secret = await window.cryptoEngine.steganosExtract({
                    imgData: buffer,
                    key: key,
                    overrideCipher: null, // Auto-detect cipher method from self-describing stream prefix
                    onProgress: ({ percent, currentBlock, totalBlocks }) => {
                        updateStegProgress(percent, currentBlock, totalBlocks, "Extracting secret message...");
                    }
                });

                updateStegProgress(100, 5, 5, "Complete!");
                stegExtractedText.value = secret;
                stegExtractedBox.style.display = "block";
                stegResultCard.classList.remove("visible");

                showToast("Secret message successfully decoded!", "success");
            } catch (err) {
                console.error(err);
                showToast(`Extraction failed: ${err.message}`, "error");
            } finally {
                stegHideBtn.disabled = false;
                stegExtractBtn.disabled = false;
                setTimeout(() => hideStegProgress(), 800);
            }
        });
    }

    if (stegCopyExtractedBtn) {
        stegCopyExtractedBtn.addEventListener("click", async () => {
            if (stegExtractedText && stegExtractedText.value) {
                await navigator.clipboard.writeText(stegExtractedText.value);
                showToast("Decoded message copied to clipboard!", "success");
            }
        });
    }

    if (stegSaveExtractedBtn) {
        stegSaveExtractedBtn.addEventListener("click", () => {
            if (stegExtractedText && stegExtractedText.value) {
                const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                if (window.promptAndDownloadText) {
                    window.promptAndDownloadText(stegExtractedText.value, `steganos_extracted_${ts}.txt`, ".txt");
                } else {
                    downloadBlob(stegExtractedText.value, `steganos_extracted_${ts}.txt`, "text/plain");
                }
            }
        });
    }

    // Steganos Preview Handlers
    if (stegPreviewBtn) {
        stegPreviewBtn.addEventListener("click", () => {
            if (stegPreviewImg && stegPreviewImg.src && window.openImagePreviewModal) {
                window.openImagePreviewModal(stegPreviewImg.src, "Steganography Output Image", "Hidden Payload Embedded PNG");
            }
        });
    }
    if (stegPreviewImg) {
        stegPreviewImg.addEventListener("click", () => {
            if (stegPreviewImg.src && window.openImagePreviewModal) {
                window.openImagePreviewModal(stegPreviewImg.src, "Steganography Output Image", "Hidden Payload Embedded PNG");
            }
        });
    }
    if (stegBeforeImg) {
        stegBeforeImg.addEventListener("click", () => {
            if (stegBeforeImg.src && window.openImagePreviewModal) {
                window.openImagePreviewModal(stegBeforeImg.src, "Steganography Carrier Image (Before)", "Original Cover Image");
            }
        });
    }

    if (stegDownloadBtn) {
        stegDownloadBtn.addEventListener("click", () => {
            if (stegResultBlob) {
                const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                if (window.promptAndDownloadBlob) {
                    window.promptAndDownloadBlob(stegResultBlob, `stego_${ts}.png`, ".png");
                } else {
                    downloadBlob(stegResultBlob, `stego_${ts}.png`, "image/png");
                }
            }
        });
    }

    // ==================== 3. PICIT (TEXT-TO-IMAGE SYNTHESIS) ====================
    let pctFile = null;
    let pctFileBuffer = null;
    let pctFilePromise = null;
    let pctResultBlob = null;

    const pctDropzone = document.getElementById("pct-dropzone");
    const pctFileInput = document.getElementById("pct-file-input");
    const pctFileCard = document.getElementById("pct-file-card");
    const pctFileName = document.getElementById("pct-file-name");
    const pctRemoveBtn = document.getElementById("pct-remove-file");

    const pctMsgInput = document.getElementById("pct-message");
    const pctKeyInput = document.getElementById("pct-key");
    const pctCipherSelect = document.getElementById("pct-cipher-select");
    const pctVigenereOptions = document.getElementById("pct-vigenere-options");
    const pctVigenerePlusCheck = document.getElementById("pct-vigenere-plus-check");

    const pctProgressBox = document.getElementById("pct-progress");
    const pctProgressFill = document.getElementById("pct-progress-fill");
    const pctProgressText = document.getElementById("pct-progress-text");
    const pctProgressSub = document.getElementById("pct-progress-sub");

    const pctGenerateBtn = document.getElementById("pct-generate-btn");
    const pctExtractBtn = document.getElementById("pct-extract-btn");

    const pctResultCard = document.getElementById("pct-result-card");
    const pctPreviewImg = document.getElementById("pct-preview-img");
    const pctDownloadBtn = document.getElementById("pct-download-btn");
    const pctExtractedBox = document.getElementById("pct-extracted-box");
    const pctExtractedText = document.getElementById("pct-extracted-text");
    const pctCopyExtractedBtn = document.getElementById("pct-copy-extracted-btn");
    const pctSaveExtractedBtn = document.getElementById("pct-save-extracted-btn");

    function updatePctProgress(percent, current, total, text = "Processing PicIt image...") {
        if (!pctProgressBox) return;
        pctProgressBox.classList.add("visible");
        if (pctProgressFill) pctProgressFill.style.width = `${percent}%`;
        if (pctProgressText) pctProgressText.textContent = `${percent}%`;
        if (pctProgressSub) pctProgressSub.textContent = `${text} (${percent}%)`;
    }

    function hidePctProgress() {
        if (!pctProgressBox) return;
        pctProgressBox.classList.remove("visible");
    }

    // Dynamic field disabling for PicIt when Binary mode selected
    function handlePctCipherChange() {
        const cipher = pctCipherSelect ? pctCipherSelect.value : "vigenere";
        const keyWrapper = pctKeyInput ? pctKeyInput.closest(".form-group") : null;
        const keyToggleBtn = document.querySelector('.password-toggle-btn[data-target="pct-key"]');

        if (pctVigenereOptions) {
            pctVigenereOptions.style.display = (cipher === "vigenere") ? "block" : "none";
        }

        if (cipher === "binary") {
            if (pctKeyInput) {
                pctKeyInput.disabled = true;
                pctKeyInput.dataset.previousValue = pctKeyInput.value;
                pctKeyInput.value = "";
                pctKeyInput.placeholder = "Key not required for binary mode";
                pctKeyInput.classList.remove("field-highlight-error");
            }
            if (keyToggleBtn) keyToggleBtn.disabled = true;
            if (keyWrapper) keyWrapper.style.opacity = "0.5";
        } else {
            if (pctKeyInput) {
                pctKeyInput.disabled = false;
                if (pctKeyInput.dataset.previousValue && !pctKeyInput.value) {
                    pctKeyInput.value = pctKeyInput.dataset.previousValue;
                }
                pctKeyInput.placeholder = "Enter key for PicIt";
            }
            if (keyToggleBtn) keyToggleBtn.disabled = false;
            if (keyWrapper) keyWrapper.style.opacity = "1";
        }
    }

    if (pctCipherSelect) {
        pctCipherSelect.addEventListener("change", handlePctCipherChange);
        handlePctCipherChange();
    }

    function setPctFile(file) {
        if (!file) return;
        pctFile = file;
        pctFileName.textContent = file.name;
        pctFileCard.classList.add("visible");
        pctDropzone.style.display = "none";
        pctResultCard.classList.remove("visible");
        pctExtractedBox.style.display = "none";
        if (pctDropzone) pctDropzone.classList.remove("field-highlight-error");

        // Immediately buffer bytes into memory while Android/mobile permission lease is fresh
        pctFileBuffer = null;
        pctFilePromise = readAsBytes(file)
            .then(buf => {
                pctFileBuffer = buf;
                return buf;
            })
            .catch(err => {
                console.warn("PicIt buffering deferred or failed:", err);
                return null;
            });
    }

    if (pctDropzone && pctFileInput) {
        pctDropzone.addEventListener("click", () => {
            pctFileInput.value = "";
            pctFileInput.click();
        });
        pctFileInput.addEventListener("click", (e) => {
            e.target.value = "";
        });
        pctDropzone.addEventListener("dragover", (e) => { e.preventDefault(); pctDropzone.classList.add("dragover"); });
        pctDropzone.addEventListener("dragleave", () => pctDropzone.classList.remove("dragover"));
        pctDropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            pctDropzone.classList.remove("dragover");
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
                setPctFile(e.dataTransfer.files[0]);
            }
        });
    }

    if (pctFileInput) {
        pctFileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) setPctFile(e.target.files[0]);
        });
    }

    if (pctRemoveBtn) {
        pctRemoveBtn.addEventListener("click", () => {
            pctFile = null;
            pctFileBuffer = null;
            pctFilePromise = null;
            if (pctFileInput) pctFileInput.value = "";
            pctFileCard.classList.remove("visible");
            pctDropzone.style.display = "block";
            pctResultCard.classList.remove("visible");
            pctExtractedBox.style.display = "none";
            hidePctProgress();
        });
    }

    // Generate PicIt Image
    if (pctGenerateBtn) {
        pctGenerateBtn.addEventListener("click", async () => {
            const message = pctMsgInput.value.trim();
            if (!message) {
                if (window.highlightField) window.highlightField("pct-message");
                return showToast("Please enter a text message to synthesize into image.", "error");
            }

            let cipher = pctCipherSelect ? pctCipherSelect.value : "vigenere";
            if (cipher === "vigenere" && pctVigenerePlusCheck && pctVigenerePlusCheck.checked) {
                cipher = "vigenere_plus";
            }
            const key = pctKeyInput ? pctKeyInput.value.trim() : "";

            if (cipher !== "binary" && !key) {
                if (window.highlightField) window.highlightField("pct-key");
                return showToast("Please provide an encryption key.", "error");
            }

            try {
                pctGenerateBtn.disabled = true;
                pctExtractBtn.disabled = true;
                hidePctProgress();
                const displayAlgo = (cipher === "vigenere_plus") ? "VIGENERE+" : cipher.toUpperCase();
                updatePctProgress(15, 1, 5, `Synthesizing image canvas with ${displayAlgo}...`);
                showToast(`Synthesizing image with ${displayAlgo} text encryption...`, "info");

                const resultBytes = await window.cryptoEngine.picitGenerate({
                    message: message,
                    key: key,
                    textCipher: cipher,
                    onProgress: ({ percent, currentBlock, totalBlocks }) => {
                        updatePctProgress(percent, currentBlock, totalBlocks, `Synthesizing image with ${displayAlgo}...`);
                    }
                });

                updatePctProgress(100, 5, 5, "Complete!");
                pctResultBlob = new Blob([resultBytes], { type: "image/png" });
                pctPreviewImg.src = URL.createObjectURL(pctResultBlob);
                pctResultCard.classList.add("visible");
                pctExtractedBox.style.display = "none";

                showToast(`Synthetic PicIt image generated using ${displayAlgo} cipher!`, "success");
            } catch (err) {
                console.error(err);
                showToast(`PicIt generation failed: ${err.message}`, "error");
            } finally {
                pctGenerateBtn.disabled = false;
                pctExtractBtn.disabled = false;
                setTimeout(() => hidePctProgress(), 800);
            }
        });
    }

    // Extract text from PicIt Image
    if (pctExtractBtn) {
        pctExtractBtn.addEventListener("click", async () => {
            if (!pctFile) {
                if (window.highlightField) window.highlightField("pct-dropzone");
                return showToast("Please select a PicIt image file to extract.", "error");
            }

            let cipher = pctCipherSelect ? pctCipherSelect.value : "vigenere";
            if (cipher === "vigenere" && pctVigenerePlusCheck && pctVigenerePlusCheck.checked) {
                cipher = "vigenere_plus";
            }
            const key = pctKeyInput ? pctKeyInput.value.trim() : "";

            if (cipher !== "binary" && !key) {
                if (window.highlightField) window.highlightField("pct-key");
                return showToast("Please provide the encryption key.", "error");
            }

            try {
                pctGenerateBtn.disabled = true;
                pctExtractBtn.disabled = true;
                hidePctProgress();
                updatePctProgress(15, 1, 5, "Extracting & decoding text from image...");
                showToast("Extracting & decoding text from PicIt image...", "info");

                let buffer = pctFileBuffer;
                if (!buffer && pctFilePromise) {
                    try {
                        buffer = await pctFilePromise;
                    } catch (e) {
                        // Fallback below
                    }
                }
                if (!buffer && pctFile) {
                    try {
                        buffer = await readAsBytes(pctFile);
                        pctFileBuffer = buffer;
                    } catch (readErr) {
                        if (window.highlightField) window.highlightField("pct-dropzone");
                        throw new Error("The image file could not be read. Please tap the file area to select it again.");
                    }
                }

                if (!buffer || buffer.byteLength === 0) {
                    throw new Error("PicIt image buffer is empty or could not be loaded.");
                }

                const secret = await window.cryptoEngine.picitExtract({
                    imgData: buffer,
                    key: key,
                    overrideCipher: null, // Auto-detect cipher method from image's encstrict pixel
                    onProgress: ({ percent, currentBlock, totalBlocks }) => {
                        updatePctProgress(percent, currentBlock, totalBlocks, "Extracting & decoding text...");
                    }
                });

                updatePctProgress(100, 5, 5, "Complete!");
                pctExtractedText.value = secret;
                pctExtractedBox.style.display = "block";
                pctResultCard.classList.remove("visible");

                showToast("Text extracted from PicIt image successfully!", "success");
            } catch (err) {
                console.error(err);
                showToast(`PicIt extraction failed: ${err.message}`, "error");
            } finally {
                pctGenerateBtn.disabled = false;
                pctExtractBtn.disabled = false;
                setTimeout(() => hidePctProgress(), 800);
            }
        });
    }

    if (pctCopyExtractedBtn) {
        pctCopyExtractedBtn.addEventListener("click", async () => {
            if (pctExtractedText && pctExtractedText.value) {
                await navigator.clipboard.writeText(pctExtractedText.value);
                showToast("Decoded message copied to clipboard!", "success");
            }
        });
    }

    if (pctSaveExtractedBtn) {
        pctSaveExtractedBtn.addEventListener("click", () => {
            if (pctExtractedText && pctExtractedText.value) {
                const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                if (window.promptAndDownloadText) {
                    window.promptAndDownloadText(pctExtractedText.value, `picit_extracted_${ts}.txt`, ".txt");
                } else {
                    downloadBlob(pctExtractedText.value, `picit_extracted_${ts}.txt`, "text/plain");
                }
            }
        });
    }

    const pctPreviewBtn = document.getElementById("pct-preview-btn");
    if (pctPreviewBtn) {
        pctPreviewBtn.addEventListener("click", () => {
            if (pctPreviewImg && pctPreviewImg.src && window.openImagePreviewModal) {
                window.openImagePreviewModal(pctPreviewImg.src, "PicIt Synthetic Image", "Generated Text-to-Pixel Canvas PNG");
            }
        });
    }
    if (pctPreviewImg) {
        pctPreviewImg.addEventListener("click", () => {
            if (pctPreviewImg.src && window.openImagePreviewModal) {
                window.openImagePreviewModal(pctPreviewImg.src, "PicIt Synthetic Image", "Generated Text-to-Pixel Canvas PNG");
            }
        });
    }

    if (pctDownloadBtn) {
        pctDownloadBtn.addEventListener("click", () => {
            if (pctResultBlob) {
                const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                if (window.promptAndDownloadBlob) {
                    window.promptAndDownloadBlob(pctResultBlob, `picit_${ts}.png`, ".png");
                } else {
                    downloadBlob(pctResultBlob, `picit_${ts}.png`, "image/png");
                }
            }
        });
    }
});
