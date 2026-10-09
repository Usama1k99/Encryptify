// Text Cryptography Suite UI Controller (Vigenere+, Scramble, XOR, Binary)

document.addEventListener("DOMContentLoaded", () => {
    const textInput = document.getElementById("text-input");
    const keyInput = document.getElementById("text-key");
    const resultOutput = document.getElementById("text-result");

    const textLenLabel = document.getElementById("text-len-label");
    const resultLenLabel = document.getElementById("result-len-label");

    const algoRadios = document.querySelectorAll('input[name="text-algo"]');
    const encryptBtn = document.getElementById("text-encrypt-btn");
    const decryptBtn = document.getElementById("text-decrypt-btn");

    const genKeyBtn = document.getElementById("text-gen-key-btn");
    const clearKeyBtn = document.getElementById("text-clear-key-btn");
    const importResultBtn = document.getElementById("text-import-result-btn");
    const copyResultBtn = document.getElementById("text-copy-result-btn");
    const downloadTextBtn = document.getElementById("text-download-btn");

    const vigenereOptions = document.getElementById("text-vigenere-options");
    const vigenerePlusCheck = document.getElementById("text-vigenere-plus-check");

    function getSelectedAlgorithm() {
        let selected = "vigenere";
        for (const radio of algoRadios) {
            if (radio.checked) {
                selected = radio.value;
                break;
            }
        }
        if (selected === "vigenere") {
            const isPlus = vigenerePlusCheck && vigenerePlusCheck.checked;
            return isPlus ? "vigenere_plus" : "vigenere";
        }
        return selected;
    }

    // Toggle key input and algorithm options when algorithm changes
    function handleAlgorithmChange() {
        let rawSelected = "vigenere";
        for (const radio of algoRadios) {
            if (radio.checked) {
                rawSelected = radio.value;
                break;
            }
        }

        if (vigenereOptions) {
            vigenereOptions.style.display = (rawSelected === "vigenere") ? "block" : "none";
        }

        const keyGroup = document.getElementById("text-key-group");
        const keyToggleBtn = document.querySelector('.password-toggle-btn[data-target="text-key"]');

        if (rawSelected === "binary") {
            if (keyInput) {
                keyInput.disabled = true;
                keyInput.dataset.previousValue = keyInput.value;
                keyInput.value = "";
                keyInput.placeholder = "Key not required for binary mode";
                keyInput.classList.remove("field-highlight-error");
            }
            if (genKeyBtn) genKeyBtn.disabled = true;
            if (clearKeyBtn) clearKeyBtn.disabled = true;
            if (keyToggleBtn) keyToggleBtn.disabled = true;
            if (keyGroup) keyGroup.style.opacity = "0.5";
        } else {
            if (keyInput) {
                keyInput.disabled = false;
                if (keyInput.dataset.previousValue && !keyInput.value) {
                    keyInput.value = keyInput.dataset.previousValue;
                }
                keyInput.placeholder = "Enter encryption key (password)";
            }
            if (genKeyBtn) genKeyBtn.disabled = false;
            if (clearKeyBtn) clearKeyBtn.disabled = false;
            if (keyToggleBtn) keyToggleBtn.disabled = false;
            if (keyGroup) keyGroup.style.opacity = "1";
        }
    }

    algoRadios.forEach(radio => {
        radio.addEventListener("change", handleAlgorithmChange);
    });
    handleAlgorithmChange(); // Initial check

    function updateLengths() {
        if (textLenLabel && textInput) {
            textLenLabel.textContent = `${textInput.value.length} characters`;
        }
        if (resultLenLabel && resultOutput) {
            resultLenLabel.textContent = `${resultOutput.value.length} characters`;
        }
    }

    if (textInput) textInput.addEventListener("input", updateLengths);

    // Random Key Generator
    if (genKeyBtn) {
        genKeyBtn.addEventListener("click", () => {
            const charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+";
            let key = "";
            const array = new Uint8Array(16);
            crypto.getRandomValues(array);
            for (let i = 0; i < array.length; i++) {
                key += charset[array[i] % charset.length];
            }
            if (keyInput) {
                keyInput.value = key;
                keyInput.dataset.previousValue = key;
            }
            showToast("Random key generated", "success");
        });
    }

    if (clearKeyBtn) {
        clearKeyBtn.addEventListener("click", () => {
            if (keyInput) {
                keyInput.value = "";
                keyInput.dataset.previousValue = "";
            }
        });
    }

    async function executeTextOperation(operation) {
        const text = textInput ? textInput.value : "";
        if (!text || !text.trim()) {
            if (window.highlightField) window.highlightField("text-input");
            return showToast("Please enter some text to process.", "error");
        }

        const algorithm = getSelectedAlgorithm();
        const key = keyInput ? keyInput.value.trim() : "";

        // Validate Key if required
        if (algorithm !== "binary" && (!key || key.length === 0)) {
            if (window.highlightField) window.highlightField("text-key");
            const algoName = algorithm === "vigenere" ? "Vigenere" : algorithm.toUpperCase();
            return showToast(`Please provide an encryption key for ${algoName}.`, "error");
        }

        // Validate Binary Inputs on Decrypt
        if (algorithm === "binary" && operation === "decrypt") {
            const clean = text.replace(/[\s,\t\r\n]/g, "");
            if (!clean) {
                if (window.highlightField) window.highlightField("text-input");
                return showToast("Please enter binary digits (0s and 1s) to decode.", "error");
            }
            if (/[^01]/.test(clean)) {
                if (window.highlightField) window.highlightField("text-input");
                return showToast("Cannot decode non-binary text. Binary input must contain only 0s and 1s.", "error");
            }
            if (clean.length % 8 !== 0) {
                if (window.highlightField) window.highlightField("text-input");
                const missing = 8 - (clean.length % 8);
                return showToast(`Incomplete binary string (${clean.length} bits). Exactly 8 bits per character are required (missing ${missing} bits).`, "error");
            }
        }

        try {
            encryptBtn.disabled = true;
            decryptBtn.disabled = true;

            const result = await window.cryptoEngine.processText({
                text: text,
                key: key,
                operation: operation,
                algorithm: algorithm
            });

            if (resultOutput) {
                resultOutput.value = result;
                updateLengths();
            }

            const algoLabel = algorithm === "vigenere_plus" ? "Vigenere+" : (algorithm === "vigenere" ? "Vigenere" : algorithm.toUpperCase());
            showToast(`Text ${operation === "encrypt" ? "encrypted" : "decrypted"} with ${algoLabel}`, "success");
        } catch (err) {
            console.error(err);
            let msg = err.message || "Text processing failed.";
            showToast(msg, "error");
        } finally {
            encryptBtn.disabled = false;
            decryptBtn.disabled = false;
        }
    }

    if (encryptBtn) encryptBtn.addEventListener("click", () => executeTextOperation("encrypt"));
    if (decryptBtn) decryptBtn.addEventListener("click", () => executeTextOperation("decrypt"));

    // Import Result -> Input
    if (importResultBtn) {
        importResultBtn.addEventListener("click", () => {
            if (resultOutput && resultOutput.value) {
                textInput.value = resultOutput.value;
                resultOutput.value = "";
                updateLengths();
                showToast("Result moved to input text", "info");
            }
        });
    }

    // Copy Result
    if (copyResultBtn) {
        copyResultBtn.addEventListener("click", async () => {
            if (resultOutput && resultOutput.value) {
                await navigator.clipboard.writeText(resultOutput.value);
                showToast("Copied to clipboard!", "success");
            }
        });
    }

    // Download Text File with Prompt & Unique Timestamp
    if (downloadTextBtn) {
        downloadTextBtn.addEventListener("click", () => {
            if (resultOutput && resultOutput.value) {
                const ts = window.getUniqueTimestamp ? window.getUniqueTimestamp() : Date.now();
                if (window.promptAndDownloadText) {
                    window.promptAndDownloadText(resultOutput.value, `text_output_${ts}.txt`, ".txt");
                } else {
                    downloadBlob(resultOutput.value, `text_output_${ts}.txt`, "text/plain");
                }
            }
        });
    }

    // Drag and drop text files directly into textarea
    if (textInput) {
        textInput.addEventListener("dragover", (e) => e.preventDefault());
        textInput.addEventListener("drop", (e) => {
            e.preventDefault();
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                const file = e.dataTransfer.files[0];
                const reader = new FileReader();
                reader.onload = (evt) => {
                    textInput.value = evt.target.result;
                    updateLengths();
                    showToast(`Imported ${file.name}`, "success");
                };
                reader.readAsText(file);
            }
        });
    }
});
