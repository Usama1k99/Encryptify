import sys
import io
from PIL import Image
from pycore import text_engine, image_engine, enigmatrix, key_utils

def test_all():
    print("=== 1. TESTING TEXT ENCRYPTION ===")
    sample_text = "The quick brown fox jumps over 13 lazy dogs! @#$%^&*()"
    key = "SuperSecretKey99!"

    # 1.1 Vigenere (Shift Only)
    v_enc = text_engine.process_text(sample_text, key, "encrypt", "vigenere")
    v_dec = text_engine.process_text(v_enc, key, "decrypt", "vigenere")
    assert v_dec == sample_text, f"Vigenere mismatch: {v_dec} != {sample_text}"
    print("[PASS] Vigenere (Shift Only) Encrypt & Decrypt")

    # 1.2 Vigenere+ (Scramble & Shift)
    vp_enc = text_engine.process_text(sample_text, key, "encrypt", "vigenere_plus")
    vp_dec = text_engine.process_text(vp_enc, key, "decrypt", "vigenere_plus")
    assert vp_dec == sample_text, f"Vigenere+ mismatch: {vp_dec} != {sample_text}"
    print("[PASS] Vigenere+ (Scramble & Shift) Encrypt & Decrypt")

    # 1.2 Scramble
    s_enc = text_engine.process_text(sample_text, key, "encrypt", "scramble")
    s_dec = text_engine.process_text(s_enc, key, "decrypt", "scramble")
    assert s_dec == sample_text, f"Scramble mismatch: {s_dec} != {sample_text}"
    print("[PASS] PRNG Scramble Encrypt & Decrypt")

    # 1.3 XOR
    x_enc = text_engine.process_text(sample_text, key, "encrypt", "xor")
    x_dec = text_engine.process_text(x_enc, key, "decrypt", "xor")
    assert x_dec == sample_text, f"XOR mismatch: {x_dec} != {sample_text}"
    print("[PASS] XOR Encrypt & Decrypt")

    # 1.4 Binary
    b_enc = text_engine.process_text(sample_text, key, "encrypt", "binary")
    b_dec = text_engine.process_text(b_enc, key, "decrypt", "binary")
    assert b_dec == sample_text, f"Binary mismatch: {b_dec} != {sample_text}"
    print("[PASS] Binary Encrypt & Decrypt")

    print("\n=== 2. TESTING ENIGMATRIX & RSA ===")
    sample_file_data = b"Hello Enigmatrix World! This is a test file for 1024x1024 block matrix encryption." * 100

    # 2.1 Symmetric Password Only
    def progress_cb(pct, blk, total):
        pass

    enc_enig = enigmatrix.encrypt_bytes(sample_file_data, key, progress_cb=progress_cb)
    dec_enig = enigmatrix.decrypt_bytes(enc_enig, raw_key=key, progress_cb=progress_cb)
    assert dec_enig == sample_file_data, "Enigmatrix symmetric decrypted data does not match original!"
    print(f"[PASS] Enigmatrix Block Matrix Encryption ({len(sample_file_data)} bytes -> {len(enc_enig)} bytes)")

    # 2.2 RSA 2048/4096 Keypair Generation & Hybrid Encryption
    print("Generating RSA test keypair...")
    priv_pem, pub_pem = key_utils.generate_rsa_keypair(key_size=2048)  # 2048 for rapid unit test
    enc_rsa = enigmatrix.encrypt_bytes(sample_file_data, key, public_key_pem=pub_pem, progress_cb=progress_cb)
    dec_rsa = enigmatrix.decrypt_bytes(enc_rsa, private_key_pem=priv_pem, progress_cb=progress_cb)
    assert dec_rsa == sample_file_data, "Enigmatrix RSA decrypted data does not match original!"
    print("[PASS] Enigmatrix RSA-OAEP Hybrid Encryption & Decryption")

    print("\n=== 3. TESTING IMAGE ENGINE ===")
    # Create test image (100x100 RGB)
    test_img = Image.new("RGB", (100, 100), color=(120, 200, 80))
    img_buf = io.BytesIO()
    test_img.save(img_buf, format="PNG")
    raw_img_bytes = img_buf.getvalue()

    # 3.1 Image XOR
    img_enc = image_engine.encrypt_image_bytes(raw_img_bytes, key)
    img_dec = image_engine.decrypt_image_bytes(img_enc, key)
    assert len(img_dec) > 0
    print("[PASS] Image XOR & Scrambling")

    # 3.2 Steganography (Key embedded)
    secret_msg = "Top secret message hidden in plain sight!"
    steg_enc = image_engine.hide_steg_data(raw_img_bytes, secret_msg, key, password_protected=False)
    steg_dec = image_engine.extract_steg_data(steg_enc)
    assert steg_dec == secret_msg, f"Stegano decoded '{steg_dec}' != '{secret_msg}'"
    print("[PASS] Steganography LSB Embed & Extract (Auto Key)")

    # 3.3 Steganography (Password protected & Multiple ciphers)
    for cipher in ["vigenere", "vigenere_plus", "scramble", "xor", "binary"]:
        steg_c = image_engine.hide_steg_data(raw_img_bytes, secret_msg, key, password_protected=True, text_cipher=cipher)
        steg_c_dec = image_engine.extract_steg_data(steg_c, key_str=key)
        assert steg_c_dec == secret_msg, f"Stegano cipher {cipher} failed: '{steg_c_dec}' != '{secret_msg}'"
        print(f"[PASS] Steganography LSB with '{cipher}' cipher verified successfully!")

    # 3.4 PicIt with Multiple Text Ciphers
    print("\n=== 4. TESTING PICIT WITH SELECTABLE TEXT CIPHERS ===")
    picit_msg = "PicIt test message with variable text cipher selection!"

    for cipher in ["vigenere", "vigenere_plus", "scramble", "xor", "binary"]:
        pct_bytes = image_engine.generate_picit_image(picit_msg, key, text_cipher=cipher)
        extracted = image_engine.extract_picit_image(pct_bytes, key)
        assert extracted == picit_msg, f"PicIt with {cipher} failed: '{extracted}' != '{picit_msg}'"
        print(f"[PASS] PicIt with '{cipher}' text cipher auto-detected & verified successfully!")

    print("\nALL CORE ENGINE TESTS PASSED 100%!")

if __name__ == '__main__':
    test_all()
