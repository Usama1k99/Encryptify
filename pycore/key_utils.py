import hashlib
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from .cfg import BLOCK_SIZE, RSA_KEY_SIZE

algorithms = {
    "blake2b": hashlib.blake2b,
    "sha512": hashlib.sha512
}

def generate_rsa_keypair(key_size=RSA_KEY_SIZE):
    """
    Generates an RSA keypair and returns both keys as PEM strings.
    """
    key = RSA.generate(key_size)
    private_pem = key.export_key().decode('utf-8')
    public_pem = key.publickey().export_key().decode('utf-8')
    return private_pem, public_pem

def detect_rsa_key(key_pem_str):
    """
    Detects if the provided PEM string is a private or public key.
    """
    if not key_pem_str:
        return None
    key_pem_str = key_pem_str.strip()
    if "PRIVATE KEY" in key_pem_str:
        return "private"
    elif "PUBLIC KEY" in key_pem_str:
        return "public"
    return None

def load_rsa_key(key_pem_bytes_or_str):
    """
    Imports a PEM formatted RSA key.
    """
    if isinstance(key_pem_bytes_or_str, str):
        key_pem_bytes_or_str = key_pem_bytes_or_str.encode('utf-8')
    return RSA.import_key(key_pem_bytes_or_str)

def rsa_encrypt_key(raw_key, public_key):
    """
    Encrypts raw symmetric key with an RSA public key using PKCS1_OAEP.
    """
    if isinstance(raw_key, str):
        raw_key = raw_key.encode('utf-8')
    if not isinstance(public_key, RSA.RsaKey):
        public_key = load_rsa_key(public_key)
    cipher = PKCS1_OAEP.new(public_key)
    return cipher.encrypt(raw_key)

def rsa_decrypt_key(encrypted_key, private_key):
    """
    Decrypts encrypted symmetric key with an RSA private key using PKCS1_OAEP.
    """
    if not isinstance(private_key, RSA.RsaKey):
        private_key = load_rsa_key(private_key)
    cipher = PKCS1_OAEP.new(private_key)
    return cipher.decrypt(encrypted_key)

def primary_hash(raw_key):
    """
    Returns SHA-512 digest of raw key.
    """
    if isinstance(raw_key, str):
        raw_key = raw_key.encode('utf-8')
    return hashlib.sha512(raw_key).digest()

def extract_prng_seeds(primary_hash_bytes):
    """
    Splits primary hash into 4 quarters and computes two 128-bit PRNG seeds.
    """
    half_len = len(primary_hash_bytes) // 2
    quarter_len = half_len // 2

    part1 = int.from_bytes(primary_hash_bytes[:quarter_len], "big")
    part2 = int.from_bytes(primary_hash_bytes[quarter_len:half_len], "big")
    part3 = int.from_bytes(primary_hash_bytes[half_len:half_len + quarter_len], "big")
    part4 = int.from_bytes(primary_hash_bytes[half_len + quarter_len:], "big")

    seed1 = part1 ^ part3
    seed2 = part2 ^ part4

    return seed1, seed2

def derive_subkey(primary_hash_bytes, raw_key, block_index):
    """
    Deterministically derives a 1MB subkey for a given block index.
    """
    if isinstance(raw_key, str):
        raw_key = raw_key.encode('utf-8')
    index_bytes = block_index.to_bytes(8, "big")
    seed = hashlib.sha512(primary_hash_bytes + raw_key + index_bytes).digest()
    return expand_subkey(seed + raw_key, "sha512")

def expand_subkey(initial_seed, algorithm_name="sha512"):
    """
    Expands an initial hash seed into a full 1MB subkey using XOR feedback.
    """
    hashing_algorithm = algorithms[algorithm_name]
    expanded_key = bytearray()

    prev_hash = hashing_algorithm(initial_seed).digest()

    while len(expanded_key) < BLOCK_SIZE:
        new_hash = hashing_algorithm(prev_hash).digest()
        xored_hash = bytes(a ^ b for a, b in zip(prev_hash, new_hash))
        expanded_key.extend(xored_hash)
        prev_hash = new_hash

    return bytes(expanded_key[:BLOCK_SIZE])
