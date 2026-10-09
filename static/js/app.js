// Global Application Logic & Notifications

// Toast Notification System
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let iconSvg = '';
    if (type === 'success') {
        iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (type === 'error') {
        iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
    } else {
        iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    toast.innerHTML = `${iconSvg} <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = '0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Download Helper for byte arrays & text
function downloadBlob(data, filename, mimeType = "application/octet-stream") {
    const blob = data instanceof Blob ? data : new Blob([data], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function getUniqueTimestamp() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const y = now.getFullYear();
    const m = pad(now.getMonth() + 1);
    const d = pad(now.getDate());
    const h = pad(now.getHours());
    const min = pad(now.getMinutes());
    const s = pad(now.getSeconds());
    return `${y}${m}${d}_${h}${min}${s}`;
}

window.getUniqueTimestamp = getUniqueTimestamp;

window.showFilenamePrompt = function(defaultFilename) {
    return new Promise((resolve) => {
        let modal = document.getElementById("filename-prompt-modal");
        if (!modal) {
            modal = document.createElement("div");
            modal.id = "filename-prompt-modal";
            modal.className = "custom-prompt-overlay";
            modal.innerHTML = `
                <div class="custom-prompt-container">
                    <div class="custom-prompt-header">
                        <div class="custom-prompt-icon">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        </div>
                        <h3 class="custom-prompt-title">Save File</h3>
                    </div>
                    <p class="custom-prompt-desc">Enter a name for your file before saving:</p>
                    <div class="form-group" style="margin-bottom: 22px;">
                        <input type="text" id="filename-prompt-input" class="input-box" spellcheck="false" autocomplete="off" placeholder="Enter filename...">
                    </div>
                    <div class="custom-prompt-actions">
                        <button type="button" class="btn btn-secondary" id="filename-prompt-cancel-btn">Cancel</button>
                        <button type="button" class="btn btn-emerald" id="filename-prompt-confirm-btn">Save File</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        const input = document.getElementById("filename-prompt-input");
        const confirmBtn = document.getElementById("filename-prompt-confirm-btn");
        const cancelBtn = document.getElementById("filename-prompt-cancel-btn");

        input.value = defaultFilename;
        modal.classList.add("open");

        setTimeout(() => {
            input.focus();
            const lastDot = defaultFilename.lastIndexOf(".");
            if (lastDot > 0) {
                input.setSelectionRange(0, lastDot);
            } else {
                input.select();
            }
        }, 50);

        const cleanup = () => {
            modal.classList.remove("open");
            confirmBtn.removeEventListener("click", onConfirm);
            cancelBtn.removeEventListener("click", onCancel);
            modal.removeEventListener("click", onBackdrop);
            document.removeEventListener("keydown", onKeyDown);
        };

        const onConfirm = () => {
            const val = input.value.trim();
            cleanup();
            resolve(val || defaultFilename);
        };

        const onCancel = () => {
            cleanup();
            resolve(null);
        };

        const onBackdrop = (e) => {
            if (e.target === modal) onCancel();
        };

        const onKeyDown = (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                onConfirm();
            } else if (e.key === "Escape") {
                e.preventDefault();
                onCancel();
            }
        };

        confirmBtn.addEventListener("click", onConfirm);
        cancelBtn.addEventListener("click", onCancel);
        modal.addEventListener("click", onBackdrop);
        document.addEventListener("keydown", onKeyDown);
    });
};

window.promptAndDownloadBlob = async function(data, defaultBaseName, requiredExt, previewLabelElementOrId) {
    if (!data) return;
    const blob = data instanceof Blob ? data : new Blob([data]);
    const ts = getUniqueTimestamp();
    
    if (requiredExt && !requiredExt.startsWith(".")) {
        requiredExt = "." + requiredExt;
    }

    let defaultFilename = defaultBaseName || `file_${ts}`;
    if (requiredExt && !defaultFilename.toLowerCase().endsWith(requiredExt.toLowerCase())) {
        defaultFilename = `${defaultFilename}${requiredExt}`;
    }

    const confirmedName = await window.showFilenamePrompt(defaultFilename);
    if (!confirmedName) return; // User pressed Cancel

    // Update preview area if provided
    if (previewLabelElementOrId) {
        const el = typeof previewLabelElementOrId === "string" ? document.getElementById(previewLabelElementOrId) : previewLabelElementOrId;
        if (el) el.textContent = confirmedName;
    }

    // No need to add extension further after user confirms the name!
    downloadBlob(blob, confirmedName, blob.type || "application/octet-stream");
    showToast(`Saved "${confirmedName}"`, "success");
};

window.promptAndDownloadText = async function(text, defaultBaseName, requiredExt = ".txt", previewLabelElementOrId) {
    if (text === undefined || text === null) return;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    await window.promptAndDownloadBlob(blob, defaultBaseName, requiredExt, previewLabelElementOrId);
};

// Format bytes
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Tab Switching
document.addEventListener("DOMContentLoaded", () => {
    // Highlight Active Navbar Link for Current Page
    const cleanPath = window.location.pathname.replace(/\.html$/, "").replace(/\/$/, "");
    const currentRoute = cleanPath.split("/").pop() || "";
    document.querySelectorAll(".nav-tab-link").forEach(link => {
        const rawHref = link.getAttribute("href") || "";
        const cleanHref = rawHref.replace(/\.html$/, "").replace(/\/$/, "");
        const linkRoute = cleanHref.split("/").pop() || "";
        if (linkRoute && linkRoute === currentRoute) {
            link.classList.add("active");
        } else if (currentRoute === "" && (cleanHref === "" || rawHref === "/")) {
            // on root / home page
            link.classList.remove("active");
        } else {
            link.classList.remove("active");
        }
    });

    const tabBtns = document.querySelectorAll(".tab-btn");
    const panels = document.querySelectorAll(".panel");

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-tab");

            tabBtns.forEach(b => b.classList.remove("active"));
            panels.forEach(p => p.classList.remove("active"));

            btn.classList.add("active");
            const activePanel = document.getElementById(target);
            if (activePanel) activePanel.classList.add("active");
        });
    });

    // Password Show/Hide Toggle System (Closed eye by default, open eye when shown)
    const eyeSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
    const eyeOffSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;

    document.querySelectorAll(".password-toggle-btn").forEach(btn => {
        btn.innerHTML = eyeOffSvg;
        btn.title = "Show key";
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const input = document.getElementById(targetId);
            if (!input || input.disabled) return;
            const willShow = input.type === "password";
            input.type = willShow ? "text" : "password";
            btn.innerHTML = willShow ? eyeSvg : eyeOffSvg;
            btn.title = willShow ? "Hide key" : "Show key";
        });
    });

    // 3-Second Missing Field Highlighter
    window.highlightField = function(elementOrId) {
        const el = typeof elementOrId === "string" ? document.getElementById(elementOrId) : elementOrId;
        if (!el) return;
        el.classList.add("field-highlight-error");
        if (typeof el.focus === "function") {
            try { el.focus(); } catch (e) {}
        }
        setTimeout(() => {
            el.classList.remove("field-highlight-error");
        }, 3000);

        const clearHighlight = () => {
            el.classList.remove("field-highlight-error");
            el.removeEventListener("input", clearHighlight);
            el.removeEventListener("change", clearHighlight);
        };
        el.addEventListener("input", clearHighlight);
        el.addEventListener("change", clearHighlight);
    };

    // Universal Text / Key File Picker
    const fileUploadSvg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`;
    const universalFileInput = document.createElement("input");
    universalFileInput.type = "file";
    universalFileInput.accept = ".txt,.key,.pem,.json,.md,.csv,*/*";
    universalFileInput.style.display = "none";
    document.body.appendChild(universalFileInput);

    let activeUploadTarget = null;
    universalFileInput.addEventListener("change", (e) => {
        if (!e.target.files || !e.target.files[0] || !activeUploadTarget) return;
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = (evt) => {
            if (activeUploadTarget) {
                activeUploadTarget.value = evt.target.result;
                activeUploadTarget.dispatchEvent(new Event("input", { bubbles: true }));
                activeUploadTarget.dispatchEvent(new Event("change", { bubbles: true }));
                activeUploadTarget.classList.remove("field-highlight-error");
                showToast(`Loaded content from "${file.name}"`, "success");
            }
            universalFileInput.value = "";
        };
        reader.onerror = () => {
            showToast("Failed to read file contents.", "error");
            universalFileInput.value = "";
        };
        reader.readAsText(file);
    });

    // Wire upload buttons
    document.querySelectorAll(".text-file-upload-btn, .text-upload-badge-btn, .input-file-btn").forEach(btn => {
        if (!btn.querySelector("svg") && !btn.textContent.trim()) {
            btn.innerHTML = fileUploadSvg;
        }
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const target = document.getElementById(targetId);
            if (!target || target.disabled) return;
            activeUploadTarget = target;
            universalFileInput.click();
        });
    });

    const statusText = document.getElementById("engine-status-text");
    const statusDot = document.getElementById("engine-status-dot");

    if (window.cryptoEngine) {
        window.cryptoEngine.addStatusListener((status) => {
            if (statusText) {
                if (status === "Encryption Engines Ready") {
                    statusText.textContent = "Ready & Private";
                } else {
                    statusText.textContent = status;
                }
            }
            if (statusDot) {
                if (status === "Encryption Engines Ready") {
                    statusDot.className = "pill-dot ready";
                } else {
                    statusDot.className = "pill-dot busy";
                }
            }
        });

        // Initialize Pyodide on page load
        window.cryptoEngine.init().catch(err => {
            console.error("Pyodide Init failed:", err);
            if (statusText) statusText.textContent = "Engine Offline";
            if (statusDot) statusDot.className = "pill-dot";
            showToast("Failed to initialize security engine. Please refresh.", "error");
        });
    }

    // Image Preview Modal System
    const imgModal = document.getElementById("image-preview-modal");
    const imgModalImg = document.getElementById("image-preview-modal-img");
    const imgModalTitle = document.getElementById("image-preview-modal-title");
    const imgModalMeta = document.getElementById("image-preview-modal-meta");
    const imgModalClose = document.getElementById("image-preview-modal-close");

    window.openImagePreviewModal = function(src, title = "Image Preview", meta = "") {
        if (!imgModal || !imgModalImg) return;
        imgModalImg.src = src;
        if (imgModalTitle) imgModalTitle.textContent = title;
        if (imgModalMeta) imgModalMeta.textContent = meta;
        imgModal.classList.add("open");
    };

    window.closeImagePreviewModal = function() {
        if (!imgModal) return;
        imgModal.classList.remove("open");
    };

    if (imgModalClose) {
        imgModalClose.addEventListener("click", window.closeImagePreviewModal);
    }
    if (imgModal) {
        imgModal.addEventListener("click", (e) => {
            if (e.target === imgModal) window.closeImagePreviewModal();
        });
    }
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") window.closeImagePreviewModal();
    });

    // Home Page Documentation Accordions
    document.querySelectorAll(".doc-card-header").forEach(header => {
        header.addEventListener("click", () => {
            const card = header.closest(".doc-engine-card");
            if (card) card.classList.toggle("active-open");
        });
    });

    document.querySelectorAll(".sub-accordion-header").forEach(subHeader => {
        subHeader.addEventListener("click", () => {
            const item = subHeader.closest(".sub-accordion-item");
            if (item) item.classList.toggle("open");
        });
    });
});
