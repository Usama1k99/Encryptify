import json
from functools import reduce
import numpy as np

# ASCII range [1..255] used in Vigenere+
ascii_values = [chr(num) for num in range(1, 256)]
ascii_len = len(ascii_values)

def get_key(strval: str) -> list[int]:
    """
    Parses key into list of integers mod 256.
    If json list of ints, returns as is. Otherwise converts each character using ord(c) % 256.
    """
    if isinstance(strval, list):
        return [int(x) % 256 for x in strval]
    try:
        k = json.loads(strval)
        if isinstance(k, list) and all(isinstance(x, int) for x in k):
            return [x % 256 for x in k]
    except Exception:
        pass
    return [abs(ord(x)) % 256 for x in strval]

def key_mod(key: list) -> list:
    """Reverses 8-bit binary representation of each key byte."""
    return [int(format(x, '08b')[::-1], 2) for x in key]

def get_seed(array: list) -> int:
    """Computes deterministic 32-bit seed from key array using Enigmatrix/Encryptify reducer."""
    if not array:
        return 12345
    max_seed = 4294967296  # 2**32
    def seed_func(a, b):
        if a % 2 == 0 and b % 2 == 0:
            return (2 * a) + b
        elif a % 2 == 0 and b % 2 != 0:
            return (2 * b) + a
        elif a % 2 != 0 and b % 2 == 0:
            return (b + a) // a if a != 0 else (b + a)
        else:
            return (a * b) + (abs(b - a) // a if a != 0 else abs(b - a))
    red_val = reduce(seed_func, array) if len(array) > 1 else array[0]
    return (red_val + (sum(array) // len(array))) % max_seed

def scramble_array(array: np.ndarray, seed: int) -> np.ndarray:
    scrambled = array.copy()
    np.random.seed(seed)
    np.random.shuffle(scrambled)
    np.random.seed()
    return scrambled

def unscramble_array(array: np.ndarray, seed: int) -> np.ndarray:
    scrambled = array.copy()
    temp = np.arange(0, len(array))
    temp = scramble_array(temp, seed)
    sorted_indices = np.argsort(temp)
    return scrambled[sorted_indices]

# ==================== 1. SCRAMBLE TEXT ====================

def scramble_encrypt(text: str, key_input) -> str:
    if not text:
        return ""
    key = get_key(key_input)
    arr = np.array([ord(x) for x in text])
    seed = get_seed(key)
    scram = scramble_array(arr, seed)
    return "".join([chr(x) for x in scram])

def scramble_decrypt(text: str, key_input) -> str:
    if not text:
        return ""
    key = get_key(key_input)
    arr = np.array([ord(x) for x in text])
    seed = get_seed(key)
    unscram = unscramble_array(arr, seed)
    return "".join([chr(x) for x in unscram])

# ==================== 2. VIGENERE+ TEXT ====================

def vigenere_encrypt(text: str, key_input) -> str:
    if not text:
        return ""
    key = get_key(key_input)
    if not key:
        return text
    # Cyclic ASCII shift only (classical Vigenere)
    ciphered = []
    k_len = len(key)
    for i, char in enumerate(text):
        shift = key[i % k_len]
        ascii_index = ord(char) + shift
        if ascii_index >= ascii_len:
            ascii_index = ascii_index % ascii_len
        elif ascii_index < 0:
            ascii_index = ascii_len - ((ascii_index * -1) % ascii_len)
        ciphered.append(ascii_values[ascii_index - 1])
    return "".join(ciphered)

def vigenere_decrypt(text: str, key_input) -> str:
    if not text:
        return ""
    key = get_key(key_input)
    if not key:
        return text
    k_len = len(key)
    deciphered = []
    for i, char in enumerate(text):
        shift = key[i % k_len]
        ascii_index = ord(char) - shift
        if ascii_index >= ascii_len:
            ascii_index = ascii_index % ascii_len
        elif ascii_index < 0:
            ascii_index = ascii_len - ((ascii_index * -1) % ascii_len)
        deciphered.append(ascii_values[ascii_index - 1])
    return "".join(deciphered)

# ==================== 3. XOR TEXT ====================

def xor_encrypt(text: str, key_input) -> str:
    if not text:
        return ""
    key = get_key(key_input)
    if not key:
        return text
    arr = np.array([ord(x) for x in text], dtype=np.uint16)
    k_mod = key_mod(key)
    size = len(arr)
    k_len = len(k_mod)
    expanded_key = (k_mod * ((size // k_len) + 1))[:size]
    arr ^= np.array(expanded_key, dtype=np.uint16)
    return "".join([chr(x) for x in arr])

def xor_decrypt(text: str, key_input) -> str:
    return xor_encrypt(text, key_input)  # XOR is self-inverting

# ==================== 4. BINARY CONVERSION ====================

def binary_encrypt(text: str) -> str:
    """Converts string into space-separated 8-bit binary representations."""
    if not text:
        raise ValueError("Please enter text to convert to binary.")
    return " ".join([format(ord(c), '08b') for c in text])

def binary_decrypt(bin_str: str) -> str:
    """Converts 8-bit binary string (with or without spaces) back into text."""
    if not bin_str or not bin_str.strip():
        raise ValueError("Please enter binary text (0s and 1s) to decode.")
    clean_bin = bin_str.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "").replace(",", "")
    if not clean_bin:
        raise ValueError("Please enter binary text (0s and 1s) to decode.")
    if any(c not in ('0', '1') for c in clean_bin):
        raise ValueError("Invalid binary input. Binary text can only contain 0s and 1s.")
    if len(clean_bin) % 8 != 0:
        bits_count = len(clean_bin)
        remainder = bits_count % 8
        raise ValueError(f"Incomplete binary sequence ({bits_count} bits). Exactly 8 bits per character are required (missing {8 - remainder} bits).")
    chars = [chr(int(clean_bin[i:i+8], 2)) for i in range(0, len(clean_bin), 8)]
    return "".join(chars)

def vigenere_plus_encrypt(text: str, key_input) -> str:
    if not text:
        return ""
    key = get_key(key_input)
    if not key:
        return text
    # Step 1: Character scramble with PRNG key seed
    scrambled = scramble_encrypt(text, key)
    # Step 2: Cyclic ASCII shift
    return vigenere_encrypt(scrambled, key)

def vigenere_plus_decrypt(text: str, key_input) -> str:
    if not text:
        return ""
    key = get_key(key_input)
    if not key:
        return text
    # Step 1: Cyclic ASCII unshift
    unshifted = vigenere_decrypt(text, key)
    # Step 2: Unscramble
    return scramble_decrypt(unshifted, key)

# ==================== UNIFIED INTERFACE ====================

def process_text(text: str, key: str, operation: str, algorithm: str) -> str:
    """
    Unified text processing function.
    algorithm: 'vigenere' | 'vigenere_plus' | 'scramble' | 'xor' | 'binary'
    operation: 'encrypt' | 'decrypt'
    """
    algorithm = algorithm.lower().strip()
    operation = operation.lower().strip()

    if algorithm == "binary":
        return binary_encrypt(text) if operation == "encrypt" else binary_decrypt(text)

    if not text or not str(text).strip():
        raise ValueError("Please enter some text to process.")

    # For ciphers requiring a key
    if not key or not str(key).strip():
        algo_display = "VIGENERE+" if "plus" in algorithm or "+" in algorithm else algorithm.upper()
        raise ValueError(f"Please provide an encryption key for {algo_display}.")

    if algorithm in ("vigenere_plus", "vigenere+", "vigenere-plus"):
        return vigenere_plus_encrypt(text, key) if operation == "encrypt" else vigenere_plus_decrypt(text, key)
    elif algorithm == "scramble":
        return scramble_encrypt(text, key) if operation == "encrypt" else scramble_decrypt(text, key)
    elif algorithm == "xor":
        return xor_encrypt(text, key) if operation == "encrypt" else xor_decrypt(text, key)
    else:  # default 'vigenere' (classical shift only)
        return vigenere_encrypt(text, key) if operation == "encrypt" else vigenere_decrypt(text, key)

