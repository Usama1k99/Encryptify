import io
import math
import random
from PIL import Image
import numpy as np
from .cfg import STEG_SIGNATURE_TEXT, STEG_PREFIX_TEXT, PICIT_SIGNATURE_TEXT
from . import text_engine

DEFAULT_COLOR = (0, 0, 0)
MAX_PIXEL_LIMIT = 2360
MAX_TEXT_LIMIT = (2 ** 24) - 1

ALGO_MAP = {
    1: "vigenere",
    2: "scramble",
    3: "xor",
    4: "binary",
    5: "vigenere_plus"
}
ALGO_REV_MAP = {v: k for k, v in ALGO_MAP.items()}
ALGO_REV_MAP["vigenere+"] = 5
ALGO_REV_MAP["vigenere-plus"] = 5

# ==================== 1. IMAGE XOR & SCRAMBLE ====================

def img_to_array(img: Image.Image) -> np.ndarray:
    return np.array(img).flatten()

def array_to_img(img_arr: np.ndarray, height: int, width: int) -> Image.Image:
    return Image.fromarray(img_arr.reshape((height, width, 3)), "RGB")

def xor_img_data(img_arr: np.ndarray, key: list) -> np.ndarray:
    size = len(img_arr)
    k_len = len(key)
    key_m = text_engine.key_mod(key)
    key_rep = (key_m * ((size // k_len) + 1))[:size]
    key_arr = np.array(key_rep, dtype=np.uint8)
    img_arr ^= key_arr
    return img_arr

def scramble_image(img: Image.Image, key: list) -> Image.Image:
    w, h = img.size
    data = img_to_array(img)
    seed = text_engine.get_seed(key[::-1])
    data = text_engine.scramble_array(data, seed)
    return array_to_img(data, height=h, width=w)

def unscramble_image(img: Image.Image, key: list) -> Image.Image:
    w, h = img.size
    data = img_to_array(img)
    seed = text_engine.get_seed(key[::-1])
    data = text_engine.unscramble_array(data, seed)
    return array_to_img(data, height=h, width=w)

def encrypt_image_bytes(img_bytes: bytes, key_str: str, progress_cb = None) -> bytes:
    if not img_bytes:
        raise ValueError("Please provide an image file.")
    if not key_str or not str(key_str).strip():
        raise ValueError("Please provide an encryption key for image scrambling.")
    if progress_cb: progress_cb(15, 1, 4)
    key = text_engine.get_key(key_str)
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise ValueError("Uploaded file is not a valid image format.")
    w, h = img.size
    if progress_cb: progress_cb(40, 2, 4)
    # 1. Scramble pixels
    scrambled = scramble_image(img, key)
    if progress_cb: progress_cb(75, 3, 4)
    # 2. XOR RGB array
    arr = img_to_array(scrambled)
    xored = xor_img_data(arr, key)
    out_img = array_to_img(xored, h, w)
    out_buf = io.BytesIO()
    out_img.save(out_buf, format="PNG")
    if progress_cb: progress_cb(100, 4, 4)
    return out_buf.getvalue()

def decrypt_image_bytes(img_bytes: bytes, key_str: str, progress_cb = None) -> bytes:
    if not img_bytes:
        raise ValueError("Please provide an image file.")
    if not key_str or not str(key_str).strip():
        raise ValueError("Please provide the encryption key used to scramble the image.")
    if progress_cb: progress_cb(15, 1, 4)
    key = text_engine.get_key(key_str)
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise ValueError("Uploaded file is not a valid image format.")
    w, h = img.size
    if progress_cb: progress_cb(45, 2, 4)
    # 1. XOR back
    arr = img_to_array(img)
    xored = xor_img_data(arr, key)
    img2 = array_to_img(xored, h, w)
    if progress_cb: progress_cb(80, 3, 4)
    # 2. Unscramble pixels
    out_img = unscramble_image(img2, key)
    out_buf = io.BytesIO()
    out_img.save(out_buf, format="PNG")
    if progress_cb: progress_cb(100, 4, 4)
    return out_buf.getvalue()

# ==================== 2. LSB STEGANOGRAPHY ====================

def to_even(n: int) -> int:
    return n if n % 2 == 0 else n - 1

def to_odd(n: int) -> int:
    return n if n % 2 != 0 else n + 1

def put_enc_tup(img: Image.Image, tup: tuple):
    pictup = img.getpixel((0, 0))
    temptup = [to_even(pictup[i]) if tup[i] == 0 else to_odd(pictup[i]) for i in range(3)]
    img.putpixel((0, 0), tuple(temptup))

def get_enc_tup(img: Image.Image) -> tuple:
    pxl = img.getpixel((0, 0))
    return tuple([int(x % 2 != 0) for x in pxl])

def put_char(img: Image.Image, dict3pix: dict, char: str, stop: bool):
    bchr = format(ord(char), '08b')
    i = 0
    for pxl, data in dict3pix.items():
        temptup = []
        for x in data:
            if i == 8:
                temptup.append(to_odd(x) if stop else to_even(x))
                break
            temptup.append(to_even(x) if bchr[i] == '0' else to_odd(x))
            i += 1
        img.putpixel(pxl, tuple(temptup))

def get_char_data(pix3list: list) -> tuple[str, bool]:
    bits = ""
    for val in pix3list:
        for ch in val:
            bits += str(int(ch % 2 != 0))
    stop = bool(int(bits[-1]))
    char = chr(int(bits[:8], 2))
    return char, stop

def hide_steg_data(img_bytes: bytes, message: str, key_str: str = None, password_protected: bool = False, text_cipher: str = "vigenere", progress_cb = None) -> bytes:
    if not img_bytes:
        raise ValueError("Please provide a cover image.")
    if not message or not str(message).strip():
        raise ValueError("Please enter a secret message to embed.")
    if password_protected and (not key_str or not str(key_str).strip()):
        raise ValueError("Please provide a password for password-protected steganography.")
    if not key_str or not str(key_str).strip():
        import secrets
        key_str = secrets.token_hex(8)
    if progress_cb: progress_cb(10, 1, 5)
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise ValueError("Carrier file is not a valid image format.")
    e_key = text_engine.get_key(key_str)
    compact_key = "".join(str(e_key)[1:-1].split())
    orientation = random.randint(0, 1)
    width, height = img.size
    ignored_pixel = (0, 0)

    sec_level = 1 if password_protected else 0
    enc_tup = (orientation, sec_level, 1 if password_protected else 0)
    put_enc_tup(img, enc_tup)

    msg = f"{STEG_SIGNATURE_TEXT} {message} {STEG_SIGNATURE_TEXT}"
    norm_cipher = (text_cipher or "vigenere").lower()
    if norm_cipher in ("vigenere_plus", "vigenere+"):
        enc_payload = text_engine.vigenere_plus_encrypt(msg, e_key)
        e_msg = f"{STEG_PREFIX_TEXT}::vigenere_plus::{enc_payload}"
    elif norm_cipher == "scramble":
        enc_payload = text_engine.scramble_encrypt(msg, e_key)
        e_msg = f"{STEG_PREFIX_TEXT}::scramble::{enc_payload}"
    elif norm_cipher == "xor":
        enc_payload = text_engine.xor_encrypt(msg, e_key)
        e_msg = f"{STEG_PREFIX_TEXT}::xor::{enc_payload}"
    elif norm_cipher == "binary":
        enc_payload = text_engine.binary_encrypt(msg)
        e_msg = f"{STEG_PREFIX_TEXT}::binary::{enc_payload}"
    else:
        enc_payload = text_engine.vigenere_encrypt(msg, e_key)
        e_msg = f"{STEG_PREFIX_TEXT}::vigenere::{enc_payload}"

    required_pixels = 1
    if sec_level == 0:
        required_pixels += 3 * (len(e_msg) + len(compact_key))
    else:
        required_pixels += 3 * len(e_msg)

    if required_pixels > (height * width):
        raise OverflowError("Text is too long to embed in this image. Please choose a larger image or shorten the text.")

    if progress_cb: progress_cb(30, 2, 5)
    i, j = 0, 0
    ti, tj = None, None

    # Embed key if not password protected
    if sec_level == 0:
        tempkey = compact_key
        dict3pix = {}
        if orientation == 0:
            while i < width and len(tempkey) > 0:
                while j < height and len(tempkey) > 0:
                    pxl = (i, j)
                    if pxl != ignored_pixel:
                        dict3pix[pxl] = img.getpixel(pxl)
                        ti, tj = i, j
                        if len(dict3pix) == 3:
                            put_char(img, dict3pix, tempkey[0], len(tempkey) == 1)
                            tempkey = tempkey[1:]
                            dict3pix = {}
                    j += 1
                i += 1
                j = 0
        else:
            while i < height and len(tempkey) > 0:
                while j < width and len(tempkey) > 0:
                    pxl = (j, i)
                    if pxl != ignored_pixel:
                        dict3pix[pxl] = img.getpixel(pxl)
                        ti, tj = i, j
                        if len(dict3pix) == 3:
                            put_char(img, dict3pix, tempkey[0], len(tempkey) == 1)
                            tempkey = tempkey[1:]
                            dict3pix = {}
                    j += 1
                i += 1
                j = 0

    if progress_cb: progress_cb(60, 3, 5)
    # Embed message
    i, j = (ti, tj) if ti is not None else (0, 0)
    temptxt = e_msg
    dict3pix = {}
    if orientation == 0:
        while i < width and len(temptxt) > 0:
            while j < height and len(temptxt) > 0:
                pxl = (i, j)
                if pxl != (ti, tj) and pxl != ignored_pixel:
                    dict3pix[pxl] = img.getpixel(pxl)
                    if len(dict3pix) == 3:
                        put_char(img, dict3pix, temptxt[0], len(temptxt) == 1)
                        temptxt = temptxt[1:]
                        dict3pix = {}
                j += 1
            i += 1
            j = 0
    else:
        while i < height and len(temptxt) > 0:
            while j < width and len(temptxt) > 0:
                pxl = (j, i)
                if pxl != (tj, ti) and pxl != ignored_pixel:
                    dict3pix[pxl] = img.getpixel(pxl)
                    if len(dict3pix) == 3:
                        put_char(img, dict3pix, temptxt[0], len(temptxt) == 1)
                        temptxt = temptxt[1:]
                        dict3pix = {}
                j += 1
            i += 1
            j = 0

    if progress_cb: progress_cb(85, 4, 5)
    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    if progress_cb: progress_cb(100, 5, 5)
    return out_buf.getvalue()

def extract_steg_data(img_bytes: bytes, key_str: str = None, override_cipher: str = None, progress_cb = None) -> str:
    if not img_bytes:
        raise ValueError("Please provide an image to extract from.")
    if progress_cb: progress_cb(15, 1, 4)
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise ValueError("Uploaded file is not a valid image format.")
    width, height = img.size
    ignored_pixel = (0, 0)

    enc_tup = get_enc_tup(img)
    if enc_tup in ((1, 0, 1), (0, 0, 1)):
        raise ValueError("This image does not contain hidden Steganography data.")

    orientation, sec_level, _ = enc_tup
    i, j = 0, 0
    ti, tj = None, None
    extracted_key = None

    if sec_level == 0:
        extracted_key = ""
        stop = False
        pix3list = []
        if orientation == 0:
            while i < width and not stop:
                while j < height and not stop:
                    pxl = (i, j)
                    if pxl != ignored_pixel:
                        pix3list.append(img.getpixel(pxl))
                        ti, tj = i, j
                        if len(pix3list) == 3:
                            char, stop = get_char_data(pix3list)
                            extracted_key += char
                            pix3list = []
                    j += 1
                i += 1
                j = 0
        else:
            while i < height and not stop:
                while j < width and not stop:
                    pxl = (j, i)
                    if pxl != ignored_pixel:
                        pix3list.append(img.getpixel(pxl))
                        ti, tj = i, j
                        if len(pix3list) == 3:
                            char, stop = get_char_data(pix3list)
                            extracted_key += char
                            pix3list = []
                    j += 1
                i += 1
                j = 0

    if progress_cb: progress_cb(50, 2, 4)
    # Read message
    i, j = (ti, tj) if ti is not None else (0, 0)
    stop = False
    rawtxt = ""
    pix3list = []
    if orientation == 0:
        while i < width and not stop:
            while j < height and not stop:
                pxl = (i, j)
                if pxl != (ti, tj) and pxl != ignored_pixel:
                    pix3list.append(img.getpixel(pxl))
                    ti, tj = i, j
                    if len(pix3list) == 3:
                        char, stop = get_char_data(pix3list)
                        rawtxt += char
                        pix3list = []
                j += 1
            i += 1
            j = 0
    else:
        while i < height and not stop:
            while j < width and not stop:
                pxl = (j, i)
                if pxl != (tj, ti) and pxl != ignored_pixel:
                    pix3list.append(img.getpixel(pxl))
                    ti, tj = i, j
                    if len(pix3list) == 3:
                        char, stop = get_char_data(pix3list)
                        rawtxt += char
                        pix3list = []
                j += 1
            i += 1
            j = 0

    if progress_cb: progress_cb(80, 3, 4)
    if not rawtxt.startswith(STEG_PREFIX_TEXT):
        raise ValueError("Could not find hidden message. The image either contains no hidden message or the wrong password was used.")

    body = rawtxt[len(STEG_PREFIX_TEXT):]
    detected_cipher = "vigenere"
    if body.startswith("::"):
        parts = body[2:].split("::", 1)
        if len(parts) == 2:
            detected_cipher = parts[0]
            body = parts[1]

    active_cipher = (override_cipher or detected_cipher).lower()
    active_key = key_str if sec_level == 1 else (f"[{extracted_key}]" if extracted_key else None)
    if active_cipher != "binary" and not active_key:
        raise ValueError("This image is password-protected. Please provide the password to extract the hidden message.")

    if active_cipher in ("vigenere_plus", "vigenere+"):
        deciphered = text_engine.vigenere_plus_decrypt(body, active_key)
    elif active_cipher == "scramble":
        deciphered = text_engine.scramble_decrypt(body, active_key)
    elif active_cipher == "xor":
        deciphered = text_engine.xor_decrypt(body, active_key)
    elif active_cipher == "binary":
        deciphered = text_engine.binary_decrypt(body)
    else:
        deciphered = text_engine.vigenere_decrypt(body, active_key)

    if progress_cb: progress_cb(100, 4, 4)
    if STEG_SIGNATURE_TEXT in deciphered:
        parts = deciphered.split(STEG_SIGNATURE_TEXT)
        if len(parts) >= 3:
            return parts[1].strip()
        return deciphered.replace(STEG_SIGNATURE_TEXT, "").strip()
    return deciphered

# ==================== 3. PICIT (TEXT-TO-SYNTHETIC IMAGE) ====================

def get_dimension(pixels: int) -> int:
    return math.ceil(math.sqrt(pixels))

def get_tuple_from_size(size: int) -> tuple[int, int, int]:
    r = size // (256 * 256)
    rem = size % (256 * 256)
    g = rem // 256
    b = rem % 256
    return (r, g, b)

def get_size_from_tuple(tup: tuple[int, int, int]) -> int:
    return (tup[0] * 256 * 256) + (tup[1] * 256) + tup[2]

def oneD_to_2DList(lst, size=3, container=tuple):
    res = []
    for i in range(0, len(lst), size):
        chunk = list(lst[i:i+size])
        while len(chunk) < size:
            chunk.append(0)
        res.append(container(chunk))
    return res

def generate_picit_image(message: str, key_str: str = None, text_cipher: str = "vigenere", progress_cb = None) -> bytes:
    """
    Synthesizes a new PNG image encoding text into RGB pixels.
    Supports selectable underlying text cipher: 'vigenere', 'scramble', 'xor', 'binary'.
    """
    if not message or not str(message).strip():
        raise ValueError("Please enter a text message to synthesize into an image.")
    text_cipher = text_cipher.lower().strip() if text_cipher else "vigenere"
    if text_cipher != "binary" and (not key_str or not str(key_str).strip()):
        raise ValueError("Please provide an encryption key for PicIt.")

    if progress_cb: progress_cb(15, 1, 5)
    key = text_engine.get_key(key_str) if key_str else []
    cipher_code = ALGO_REV_MAP.get(text_cipher, 1)
    enc_strictness = (1, cipher_code, 0)

    # Wrap message with signature
    wrapped_msg = f"{PICIT_SIGNATURE_TEXT} {message} {PICIT_SIGNATURE_TEXT}"
    encrypted_text = text_engine.process_text(wrapped_msg, key, "encrypt", text_cipher)
    if progress_cb: progress_cb(35, 2, 5)

    orientation = random.randint(0, 1)
    required_pixels = 6
    key_tup = oneD_to_2DList(key, 3, tuple)
    enc_ord = [ord(x) % 256 for x in encrypted_text]
    enc_tup = oneD_to_2DList(enc_ord, 3, tuple)
    required_pixels += (len(enc_tup) + len(key_tup))

    img_len = get_dimension(required_pixels)
    if img_len > MAX_PIXEL_LIMIT or len(encrypted_text) > MAX_TEXT_LIMIT:
        raise OverflowError("Text size too big. Divide into smaller chunks.")

    ti_len = img_len - 1
    map_to_pixel = {
        'txtlen': (0, 0),
        'txtco-ord': (0, ti_len),
        'keylen': (ti_len, 0),
        'keyco-ord': (ti_len, ti_len),
        'encstrict': ((0, 1), (1, 0))
    }
    ignored_pixels = [(0, 0), (0, ti_len), (ti_len, 0), (ti_len, ti_len), (1, 0), (0, 1)]

    img = Image.new("RGB", (img_len, img_len), DEFAULT_COLOR)
    img.putpixel(map_to_pixel['encstrict'][0], enc_strictness)
    img.putpixel(map_to_pixel['encstrict'][1], enc_strictness)
    img.putpixel(map_to_pixel['txtlen'], get_tuple_from_size(len(encrypted_text)))
    img.putpixel(map_to_pixel['keyco-ord'], (0, orientation, 0))

    tctup = (0, 0, 0)
    count = 0
    index = 0
    i, j = 0, 0

    while (i < img_len or j < img_len) and index < len(enc_tup):
        if count != 0:
            j = 0
        while j < img_len and index < len(enc_tup):
            t = enc_tup[index]
            pxl = (i, j) if orientation == 0 else (j, i)
            if pxl not in ignored_pixels:
                if count == 0:
                    tctup = (i, random.randint(0, 255), j) if orientation == 0 else (j, random.randint(0, 255), i)
                    count += 1
                img.putpixel(pxl, t)
                index += 1
            j += 1
        i += 1

    img.putpixel(map_to_pixel['txtco-ord'], tctup)
    if progress_cb: progress_cb(70, 3, 5)
    # Scramble final canvas using key
    img = scramble_image(img, key)
    if progress_cb: progress_cb(90, 4, 5)

    out_buf = io.BytesIO()
    img.save(out_buf, format="PNG")
    if progress_cb: progress_cb(100, 5, 5)
    return out_buf.getvalue()

def extract_picit_image(img_bytes: bytes, key_str: str = None, override_cipher: str = None, progress_cb = None) -> str:
    """
    Extracts text from a PicIt synthetic PNG image.
    Automatically detects cipher mode from encstrictness pixel, or respects override_cipher.
    """
    if not img_bytes:
        raise ValueError("Please select a PicIt image file to extract.")
    if progress_cb: progress_cb(15, 1, 5)
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception:
        raise ValueError("Uploaded file is not a valid image format.")
    w, h = img.size
    if w != h:
        raise ValueError("Image is not square. PicIt images must be square images generated by PicIt.")

    key = text_engine.get_key(key_str) if key_str else []

    ti_len = w - 1
    map_to_pixel = {
        'txtlen': (0, 0),
        'txtco-ord': (0, ti_len),
        'keylen': (ti_len, 0),
        'keyco-ord': (ti_len, ti_len),
        'encstrict': ((0, 1), (1, 0))
    }
    ignored_pixels = [(0, 0), (0, ti_len), (ti_len, 0), (ti_len, ti_len), (1, 0), (0, 1)]

    # Unscramble image
    img = unscramble_image(img, key)
    if progress_cb: progress_cb(40, 2, 5)

    # Check orientation / rotation
    p01, p10 = img.getpixel(map_to_pixel['encstrict'][0]), img.getpixel(map_to_pixel['encstrict'][1])
    for _ in range(3):
        if p01 != p10:
            img = scramble_image(img, key)
            img = img.rotate(angle=90)
            img = unscramble_image(img, key)
            p01, p10 = img.getpixel(map_to_pixel['encstrict'][0]), img.getpixel(map_to_pixel['encstrict'][1])
        else:
            break

    if p01 != p10:
        raise ValueError("Could not decode PicIt image. The key may be incorrect or the image is not a PicIt file.")

    if progress_cb: progress_cb(65, 3, 5)
    # Detect cipher
    cipher_code = p01[1]
    detected_cipher = ALGO_MAP.get(cipher_code, "vigenere")
    active_cipher = override_cipher if override_cipher else detected_cipher

    tltup = img.getpixel(map_to_pixel['txtlen'])
    tctup = img.getpixel(map_to_pixel['txtco-ord'])
    kctup = img.getpixel(map_to_pixel['keyco-ord'])

    orientation = kctup[1]
    text_length = get_size_from_tuple(tltup)
    txtuplen = int(text_length / 3) + 1

    temp_tl = txtuplen
    i, _x, j = tctup
    if orientation == 1:
        i, j = j, i

    count = 0
    text_list = []
    while (i < w or j < w) and temp_tl > 0:
        if count != 0:
            j = 0
        else:
            count += 1
        while j < w and temp_tl > 0:
            pxl = (i, j) if orientation == 0 else (j, i)
            if pxl not in ignored_pixels:
                t = img.getpixel(pxl)
                temp_tl -= 1
                for v in t:
                    text_list.append(v)
            j += 1
        i += 1

    raw_extracted = "".join([chr(x) for x in text_list[:text_length]])
    if progress_cb: progress_cb(85, 4, 5)
    deciphered = text_engine.process_text(raw_extracted, key, "decrypt", active_cipher)
    if progress_cb: progress_cb(100, 5, 5)

    if PICIT_SIGNATURE_TEXT in deciphered:
        parts = deciphered.split(PICIT_SIGNATURE_TEXT)
        if len(parts) >= 3:
            return parts[1].strip()
        return deciphered.replace(PICIT_SIGNATURE_TEXT, "").strip()
    return deciphered
