// Enigmatrix File Encryption & RSA UI Controller

document.addEventListener("DOMContentLoaded", () => {
    let selectedFile = null;
    let processedResult = null;
    let isProcessing = false;

    // Elements
    const dropzone = document.getElementById("enig-dropzone");
    const fileInput = document.getElementById("enig-file-input");
    const fileCard = document.getElementById("enig-file-card");
    const fileNameEl = document.getElementById("enig-file-name");
    const fileMetaEl = document.getElementById("enig-file-meta");
    const removeFileBtn = document.getElementById("enig-remove-file");

    const keyInput = document.getElementById("enig-key");
    const rsaToggle = document.getElementById("enig-rsa-toggle");
    const rsaOptions = document.getElementById("enig-rsa-options");
    const rsaPemInput = document.getElementById("enig-rsa-pem");
    const rsaFileInput = document.getElementById("enig-rsa-file-input");

    const encryptBtn = document.getElementById("enig-encrypt-btn");
    const decryptBtn = document.getElementById("enig-decrypt-btn");

    const progressBox = document.getElementById("enig-progress");
    const progressFill = document.getElementById("enig-progress-fill");
    const progressText = document.getElementById("enig-progress-text");
    const progressSub = document.getElementById("enig-progress-sub");

    const resultBox = document.getElementById("enig-result");
    const resultName = document.getElementById("enig-result-name");
    const resultMeta = document.getElementById("enig-result-meta");
    const downloadBtn = document.getElementById("enig-download-btn");

    // RSA Modal Elements
    const openRsaModalBtn = document.getElementById("open-rsa-modal-btn");
    const rsaModal = document.getElementById("rsa-modal");
    const closeRsaModalBtn = document.getElementById("close-rsa-modal-btn");
    const genRsaBtn = document.getElementById("gen-rsa-btn");
    const rsaKeySizeSelect = document.getElementById("rsa-key-size");
    const rsaOutputBox = document.getElementById("rsa-output-box");
    const rsaPublicPemText = document.getElementById("rsa-public-pem");
    const rsaPrivatePemText = document.getElementById("rsa-private-pem");
    const downloadPubBtn = document.getElementById("download-pub-btn");
    const downloadPrivBtn = document.getElementById("download-priv-btn");

    // File Selection Handlers
    function setFile(file) {
        if (!file) return;
        selectedFile = file;
        fileNameEl.textContent = file.name;
        fileMetaEl.textContent = formatFileSize(file.size);
        fileCard.classList.add("visible");
        dropzone.style.display = "none";
        resultBox.classList.remove("visible");
    }

    function clearFile() {
        selectedFile = null;
        fileInput.value = "";
        fileCard.classList.remove("visible");
        dropzone.style.display = "block";
    }

    if (dropzone) {
        dropzone.addEventListener("click", () => fileInput.click());
        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        });
        dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                setFile(e.dataTransfer.files[0]);
            }
        });
    }

    if (fileInput) {
        fileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
        });
    }

    if (removeFileBtn) removeFileBtn.addEventListener("click", clearFile);

    // RSA Toggle
    if (rsaToggle) {
        rsaToggle.addEventListener("change", (e) => {
            if (rsaOptions) {
                rsaOptions.style.display = e.target.checked ? "block" : "none";
            }
        });
    }

    // Load PEM file into textarea
    if (rsaFileInput) {
        rsaFileInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files[0]) {
                const reader = new FileReader();
                reader.onload = (evt) => {
                    if (rsaPemInput) rsaPemInput.value = evt.target.result;
                    showToast("RSA Key file loaded", "success");
                };
                reader.readAsText(e.target.files[0]);
            }
        });
    }

    // Progress updates
    function updateProgress(percent, current, total) {
        if (!progressBox) return;
        progressBox.classList.add("visible");
        progressFill.style.width = `${percent}%`;
        progressText.textContent = `${percent}%`;
        progressSub.textContent = `Processing block ${current} of ${total}...`;
    }

    function hideProgress() {
        if (progressBox) progressBox.classList.remove("visible");
    }

    // Enigmatrix Encrypt Handler
    if (encryptBtn) {
        encryptBtn.addEventListener("click", async () => {
            if (!selectedFile) {
                if (window.highlightField) window.highlightField("enig-dropzone");
                return showToast("Please select a file to encrypt.", "error");
            }
            const key = keyInput.value.trim();
            if (key.length < 4) {
                if (window.highlightField) window.highlightField("enig-key");
                return showToast("Password key must be at least 4 characters.", "error");
            }

            const useRsa = rsaToggle && rsaToggle.checked;
            const pemKey = useRsa ? rsaPemInput.value.trim() : null;

            if (useRsa && !pemKey) {
                if (window.highlightField) window.highlightField("enig-rsa-pem");
                return showToast("Please provide an RSA Public Key for RSA mode.", "error");
            }

            try {
                isProcessing = true;
                encryptBtn.disabled = true;
                decryptBtn.disabled = true;
                resultBox.classList.remove("visible");

                showToast("Encrypting file...", "info");
                const buffer = new Uint8Array(await selectedFile.arrayBuffer());

                const result = await window.cryptoEngine.enigmatrixEncrypt({
                    fileData: buffer,
                    key: key,
                    publicKeyPem: pemKey,
                    onProgress: ({ percent, currentBlock, totalBlocks }) => {
                        updateProgress(percent, currentBlock, totalBlocks);
                    }
                });

                const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                const defaultEncName = `${selectedFile.name.replace(/\.emx$/i, "")}_${ts}.emx`;

                processedResult = {
                    data: result,
                    name: defaultEncName,
                    size: result.byteLength,
                    ext: ".emx"
                };

                resultName.textContent = processedResult.name;
                resultMeta.textContent = `Encrypted (${formatFileSize(processedResult.size)})`;
                resultBox.classList.add("visible");
                showToast("File encrypted successfully!", "success");
            } catch (err) {
                console.error(err);
                let msg = err.message || "Encryption failed.";
                showToast(msg, "error");
            } finally {
                isProcessing = false;
                encryptBtn.disabled = false;
                decryptBtn.disabled = false;
                hideProgress();
            }
        });
    }

    // Enigmatrix Decrypt Handler
    if (decryptBtn) {
        decryptBtn.addEventListener("click", async () => {
            if (!selectedFile) {
                if (window.highlightField) window.highlightField("enig-dropzone");
                return showToast("Please select a file to decrypt.", "error");
            }
            const key = keyInput.value.trim();
            const useRsa = rsaToggle && rsaToggle.checked;
            const pemKey = useRsa ? rsaPemInput.value.trim() : null;

            if (!key && !pemKey) {
                if (window.highlightField) window.highlightField(useRsa ? "enig-rsa-pem" : "enig-key");
                return showToast("Provide your password or RSA Private Key to decrypt.", "error");
            }

            try {
                isProcessing = true;
                encryptBtn.disabled = true;
                decryptBtn.disabled = true;
                resultBox.classList.remove("visible");

                showToast("Decrypting file...", "info");
                const buffer = new Uint8Array(await selectedFile.arrayBuffer());

                const result = await window.cryptoEngine.enigmatrixDecrypt({
                    fileData: buffer,
                    key: key,
                    privateKeyPem: pemKey,
                    onProgress: ({ percent, currentBlock, totalBlocks }) => {
                        updateProgress(percent, currentBlock, totalBlocks);
                    }
                });

                const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                const baseClean = selectedFile.name.replace(/\.emx$/i, "").replace(/\.enig$/i, "");
                const defaultDecName = `${baseClean}_decrypted_${ts}.emx`;

                processedResult = {
                    data: result,
                    name: defaultDecName,
                    size: result.byteLength,
                    ext: ".emx"
                };

                resultName.textContent = processedResult.name;
                resultMeta.textContent = `Decrypted (${formatFileSize(processedResult.size)})`;
                resultBox.classList.add("visible");
                showToast("File decrypted successfully!", "success");
            } catch (err) {
                console.error(err);
                let msg = err.message || "Decryption failed. Please check your password or key.";
                showToast(msg, "error");
            } finally {
                isProcessing = false;
                encryptBtn.disabled = false;
                decryptBtn.disabled = false;
                hideProgress();
            }
        });
    }

    // Download Result File
    if (downloadBtn) {
        downloadBtn.addEventListener("click", () => {
            if (processedResult) {
                if (window.promptAndDownloadBlob) {
                    window.promptAndDownloadBlob(processedResult.data, processedResult.name, processedResult.ext || ".emx", "enig-result-name");
                } else {
                    downloadBlob(processedResult.data, processedResult.name);
                }
            }
        });
    }

    // RSA Modal Handlers
    if (openRsaModalBtn && rsaModal) {
        openRsaModalBtn.addEventListener("click", () => rsaModal.classList.add("open"));
    }
    if (closeRsaModalBtn && rsaModal) {
        closeRsaModalBtn.addEventListener("click", () => rsaModal.classList.remove("open"));
    }

    if (genRsaBtn) {
        genRsaBtn.addEventListener("click", async () => {
            const size = parseInt(rsaKeySizeSelect.value, 10) || 4096;
            try {
                genRsaBtn.disabled = true;
                genRsaBtn.textContent = `Generating ${size}-bit RSA Keypair...`;
                showToast(`Generating ${size}-bit keypair in WebAssembly (this takes a moment)...`, "info");

                const { privatePem, publicPem } = await window.cryptoEngine.generateRsaKeypair(size);

                rsaPublicPemText.value = publicPem;
                rsaPrivatePemText.value = privatePem;
                rsaOutputBox.style.display = "block";

                downloadPubBtn.onclick = () => {
                    const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                    window.promptAndDownloadText(publicPem, `rsa_public_${ts}.pem`, ".pem");
                };
                downloadPrivBtn.onclick = () => {
                    const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                    window.promptAndDownloadText(privatePem, `rsa_private_${ts}.pem`, ".pem");
                };

                showToast("RSA Keypair generated successfully!", "success");
            } catch (err) {
                console.error(err);
                showToast(`RSA Key generation failed: ${err.message}`, "error");
            } finally {
                genRsaBtn.disabled = false;
                genRsaBtn.textContent = "Generate New RSA Keypair";
            }
        });
    }
});
