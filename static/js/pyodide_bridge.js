// Client-side Promise-based bridge to the Pyodide Web Worker

class CryptoEngineBridge {
    constructor() {
        this.worker = null;
        this.isReady = false;
        this.initPromise = null;
        this.pendingRequests = new Map();
        this.progressCallbacks = new Map();
        this.statusListeners = new Set();
        this.msgCounter = 0;
    }

    addStatusListener(fn) {
        this.statusListeners.add(fn);
    }

    removeStatusListener(fn) {
        this.statusListeners.delete(fn);
    }

    notifyStatus(status) {
        this.statusListeners.forEach(fn => fn(status));
    }

    init() {
        if (this.initPromise) return this.initPromise;

        this.initPromise = new Promise((resolve, reject) => {
            this.worker = new Worker("static/js/worker.js");

            this.worker.onmessage = (e) => {
                const { type, id, result, message, percent, currentBlock, totalBlocks } = e.data;

                if (type === "STATUS") {
                    this.notifyStatus(message);
                } else if (type === "READY") {
                    this.isReady = true;
                    this.notifyStatus("Encryption Engines Ready");
                    resolve();
                } else if (type === "PROGRESS") {
                    if (id && this.progressCallbacks.has(id)) {
                        this.progressCallbacks.get(id)({ percent, currentBlock, totalBlocks });
                    } else {
                        // Global progress event
                        this.progressCallbacks.forEach(cb => cb({ percent, currentBlock, totalBlocks }));
                    }
                } else if (type === "SUCCESS") {
                    if (this.pendingRequests.has(id)) {
                        const { resolveReq } = this.pendingRequests.get(id);
                        this.pendingRequests.delete(id);
                        this.progressCallbacks.delete(id);
                        resolveReq(result);
                    }
                } else if (type === "ERROR") {
                    if (id && this.pendingRequests.has(id)) {
                        const { rejectReq } = this.pendingRequests.get(id);
                        this.pendingRequests.delete(id);
                        this.progressCallbacks.delete(id);
                        rejectReq(new Error(message));
                    } else if (!this.isReady) {
                        reject(new Error(message));
                    } else {
                        console.error("[Engine Error]", message);
                    }
                }
            };

            this.worker.onerror = (err) => {
                console.error("[Worker Error]", err);
                reject(err);
            };

            this.worker.postMessage({ action: "INIT" });
        });

        return this.initPromise;
    }

    _send(action, payload, transferables = [], onProgress = null) {
        const id = ++this.msgCounter;
        return new Promise((resolveReq, rejectReq) => {
            this.pendingRequests.set(id, { resolveReq, rejectReq });
            if (onProgress) {
                this.progressCallbacks.set(id, onProgress);
            }
            this.worker.postMessage({ action, id, payload }, transferables);
        });
    }

    // Text Engine
    async processText({ text, key, operation, algorithm }) {
        await this.init();
        return this._send("TEXT_PROCESS", { text, key, operation, algorithm });
    }

    // Enigmatrix File Engine
    async enigmatrixEncrypt({ fileData, key, publicKeyPem, onProgress }) {
        await this.init();
        return this._send("ENIGMATRIX_ENCRYPT", { fileData, key, publicKeyPem }, [fileData.buffer], onProgress);
    }

    async enigmatrixDecrypt({ fileData, key, privateKeyPem, onProgress }) {
        await this.init();
        return this._send("ENIGMATRIX_DECRYPT", { fileData, key, privateKeyPem }, [fileData.buffer], onProgress);
    }

    // RSA Key Utilities
    async generateRsaKeypair(keySize = 4096) {
        await this.init();
        return this._send("RSA_GENERATE", { keySize });
    }

    // Image XOR
    async processImageXor({ imgData, key, operation, onProgress }) {
        await this.init();
        return this._send("IMAGE_XOR", { imgData, key, operation }, [imgData.buffer], onProgress);
    }

    // Steganography
    async steganosHide({ imgData, message, key, passwordProtected, textCipher, onProgress }) {
        await this.init();
        return this._send("STEGANOS_HIDE", { imgData, message, key, passwordProtected, textCipher }, [imgData.buffer], onProgress);
    }

    async steganosExtract({ imgData, key, overrideCipher, onProgress }) {
        await this.init();
        return this._send("STEGANOS_EXTRACT", { imgData, key, overrideCipher }, [imgData.buffer], onProgress);
    }

    // PicIt (with configurable text cipher)
    async picitGenerate({ message, key, textCipher, onProgress }) {
        await this.init();
        return this._send("PICIT_GENERATE", { message, key, textCipher }, [], onProgress);
    }

    async picitExtract({ imgData, key, overrideCipher, onProgress }) {
        await this.init();
        return this._send("PICIT_EXTRACT", { imgData, key, overrideCipher }, [imgData.buffer], onProgress);
    }
}

// Global instance
window.cryptoEngine = new CryptoEngineBridge();
