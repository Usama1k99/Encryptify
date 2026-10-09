// Web Worker for In-Browser Pyodide Execution
/* global importScripts, loadPyodide */

let pyodide = null;
let isReady = false;

// Send message helper
function sendMsg(type, payload = {}) {
    self.postMessage({ type, ...payload });
}

let currentActionId = null;

// Progress callback wrapper called from Python
self.pythonProgressCallback = function(percent, currentBlock, totalBlocks) {
    sendMsg("PROGRESS", { id: currentActionId, percent, currentBlock, totalBlocks });
};

async function initPyodide() {
    try {
        sendMsg("STATUS", { message: "Starting security engine..." });
        importScripts("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js");
        
        pyodide = await loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"
        });

        sendMsg("STATUS", { message: "Loading encryption modules..." });
        await pyodide.loadPackage(["numpy", "pycryptodome", "pillow"]);

        sendMsg("STATUS", { message: "Finalizing security tools..." });
        
        // Create pycore directory in Pyodide VFS
        pyodide.FS.mkdirTree("/home/pyodide/pycore");

        // Fetch core python files
        const coreFiles = [
            "cfg.py",
            "key_utils.py",
            "enigmatrix.py",
            "text_engine.py",
            "image_engine.py",
            "__init__.py"
        ];

        for (const file of coreFiles) {
            let resp = await fetch(`/pycore/${file}?v=${Date.now()}`);
            if (!resp.ok) {
                resp = await fetch(`pycore/${file}?v=${Date.now()}`);
            }
            if (!resp.ok) {
                throw new Error(`Failed to load engine file: ${file} (HTTP ${resp.status})`);
            }
            const content = await resp.text();
            pyodide.FS.writeFile(`/home/pyodide/pycore/${file}`, content);
        }

        // Register python progress callback
        pyodide.runPython(`
import sys
sys.path.insert(0, '/home/pyodide')
import js
from pycore import text_engine, image_engine, enigmatrix, key_utils

def py_progress(pct, cur, tot):
    js.pythonProgressCallback(pct, cur, tot)
`);

        isReady = true;
        sendMsg("READY");
    } catch (err) {
        sendMsg("ERROR", { message: `Engine Initialization Failed: ${err.message}` });
    }
}

self.onmessage = async function(e) {
    const { action, id, payload } = e.data;
    currentActionId = id;

    if (action === "INIT") {
        if (!isReady) await initPyodide();
        else sendMsg("READY");
        return;
    }

    if (!isReady) {
        sendMsg("ERROR", { id, message: "Engine not ready yet. Please wait..." });
        return;
    }

    try {
        switch (action) {
            case "TEXT_PROCESS": {
                const { text, key, operation, algorithm } = payload;
                pyodide.globals.set("t_in", text);
                pyodide.globals.set("t_key", key);
                pyodide.globals.set("t_op", operation);
                pyodide.globals.set("t_algo", algorithm);
                const res = pyodide.runPython(`
text_engine.process_text(t_in, t_key, t_op, t_algo)
`);
                sendMsg("SUCCESS", { id, result: res });
                break;
            }

            case "ENIGMATRIX_ENCRYPT": {
                const { fileData, key, publicKeyPem } = payload;
                pyodide.globals.set("f_bytes", fileData);
                pyodide.globals.set("e_key", key);
                pyodide.globals.set("e_pub", publicKeyPem || null);
                const pyCode = `
raw_in = bytes(f_bytes)
enigmatrix.encrypt_bytes(raw_in, e_key, public_key_pem=e_pub, progress_cb=py_progress)
`;
                const encBytes = pyodide.runPython(pyCode);
                const jsArray = new Uint8Array(encBytes.toJs());
                sendMsg("SUCCESS", { id, result: jsArray }, [jsArray.buffer]);
                break;
            }

            case "ENIGMATRIX_DECRYPT": {
                const { fileData, key, privateKeyPem } = payload;
                pyodide.globals.set("f_bytes", fileData);
                pyodide.globals.set("d_key", key || null);
                pyodide.globals.set("d_priv", privateKeyPem || null);
                const pyCode = `
raw_in = bytes(f_bytes)
enigmatrix.decrypt_bytes(raw_in, raw_key=d_key, private_key_pem=d_priv, progress_cb=py_progress)
`;
                const decBytes = pyodide.runPython(pyCode);
                const jsArray = new Uint8Array(decBytes.toJs());
                sendMsg("SUCCESS", { id, result: jsArray }, [jsArray.buffer]);
                break;
            }

            case "RSA_GENERATE": {
                const keySize = payload.keySize || 4096;
                pyodide.globals.set("k_size", keySize);
                const res = pyodide.runPython(`
priv, pub = key_utils.generate_rsa_keypair(k_size)
(priv, pub)
`);
                const [privatePem, publicPem] = res.toJs();
                sendMsg("SUCCESS", { id, result: { privatePem, publicPem } });
                break;
            }

            case "IMAGE_XOR": {
                const { imgData, key, operation } = payload;
                pyodide.globals.set("img_raw", imgData);
                pyodide.globals.set("ix_key", key);
                const pyCode = operation === "encrypt" 
                    ? `image_engine.encrypt_image_bytes(bytes(img_raw), ix_key, progress_cb=py_progress)`
                    : `image_engine.decrypt_image_bytes(bytes(img_raw), ix_key, progress_cb=py_progress)`;
                const resBytes = pyodide.runPython(pyCode);
                const jsArray = new Uint8Array(resBytes.toJs());
                sendMsg("SUCCESS", { id, result: jsArray }, [jsArray.buffer]);
                break;
            }

            case "STEGANOS_HIDE": {
                const { imgData, message, key, passwordProtected, textCipher } = payload;
                pyodide.globals.set("steg_img", imgData);
                pyodide.globals.set("steg_msg", message);
                pyodide.globals.set("steg_key", key);
                pyodide.globals.set("steg_prot", passwordProtected);
                pyodide.globals.set("steg_cipher", textCipher || "vigenere");
                const resBytes = pyodide.runPython(`
image_engine.hide_steg_data(bytes(steg_img), steg_msg, steg_key, password_protected=steg_prot, text_cipher=steg_cipher, progress_cb=py_progress)
`);
                const jsArray = new Uint8Array(resBytes.toJs());
                sendMsg("SUCCESS", { id, result: jsArray }, [jsArray.buffer]);
                break;
            }

            case "STEGANOS_EXTRACT": {
                const { imgData, key, overrideCipher } = payload;
                pyodide.globals.set("steg_img", imgData);
                pyodide.globals.set("steg_key", key || null);
                pyodide.globals.set("steg_cipher", overrideCipher || null);
                const extractedMsg = pyodide.runPython(`
image_engine.extract_steg_data(bytes(steg_img), key_str=steg_key, override_cipher=steg_cipher, progress_cb=py_progress)
`);
                sendMsg("SUCCESS", { id, result: extractedMsg });
                break;
            }

            case "PICIT_GENERATE": {
                const { message, key, textCipher } = payload;
                pyodide.globals.set("pct_msg", message);
                pyodide.globals.set("pct_key", key);
                pyodide.globals.set("pct_algo", textCipher || "vigenere");
                const resBytes = pyodide.runPython(`
image_engine.generate_picit_image(pct_msg, pct_key, text_cipher=pct_algo, progress_cb=py_progress)
`);
                const jsArray = new Uint8Array(resBytes.toJs());
                sendMsg("SUCCESS", { id, result: jsArray }, [jsArray.buffer]);
                break;
            }

            case "PICIT_EXTRACT": {
                const { imgData, key, overrideCipher } = payload;
                pyodide.globals.set("pct_img", imgData);
                pyodide.globals.set("pct_key", key);
                pyodide.globals.set("pct_ovr", overrideCipher || null);
                const extractedMsg = pyodide.runPython(`
image_engine.extract_picit_image(bytes(pct_img), pct_key, override_cipher=pct_ovr, progress_cb=py_progress)
`);
                sendMsg("SUCCESS", { id, result: extractedMsg });
                break;
            }

            default:
                throw new Error(`Unknown action: ${action}`);
        }
    } catch (err) {
        let msg = err.message || "An error occurred during processing.";
        const match = msg.match(/(?:[A-Za-z0-9_]+Error|Exception):\s*(.+)/);
        if (match && match[1]) {
            msg = match[1].split("\n")[0].trim();
        } else if (msg.includes("PythonError:")) {
            const lines = msg.split("\n").filter(l => l.trim().length > 0);
            msg = lines[lines.length - 1].replace(/^[A-Za-z0-9_]+:\s*/, "").trim();
        }
        sendMsg("ERROR", { id, message: msg });
    }
};
