import io
import struct
import random
import numpy as np
from .cfg import BLOCK_SIZE, MATRIX_SIZE, SWAP_COUNT
from . import key_utils

OPERATIONS = ["permutation", "xor", "modular"]
MOD_ORDER = ["add", "sub"]
PERMUTATION_ORDER = ["row", "column"]

def bytes_to_matrix(block):
    """Converts a 1MB byte block into a 1024x1024 numpy uint8 matrix."""
    if len(block) != BLOCK_SIZE:
        raise ValueError(f"Block size must be exactly {BLOCK_SIZE} bytes (got {len(block)})")
    return np.frombuffer(block, dtype=np.uint8).reshape(MATRIX_SIZE, MATRIX_SIZE)

def matrix_to_bytes(matrix):
    """Converts a 1024x1024 matrix back to 1MB byte string."""
    if matrix.shape != (MATRIX_SIZE, MATRIX_SIZE):
        raise ValueError(f"Matrix shape must be ({MATRIX_SIZE}, {MATRIX_SIZE})")
    return matrix.astype(np.uint8).tobytes()

def pad_block(block):
    """Pads a block to 1MB with null bytes."""
    padding_length = BLOCK_SIZE - len(block)
    return block + b'\x00' * padding_length

def truncate_block(block, original_size):
    """Trims block to original size."""
    return block[:original_size]

def apply_xor(matrix, subkey):
    return matrix ^ subkey

def apply_permutation(matrix, row_swaps, col_swaps, order):
    temp = matrix.copy()
    if order[0] == "row":
        for i, j in row_swaps:
            temp[[i, j], :] = temp[[j, i], :]
        for i, j in col_swaps:
            temp[:, [i, j]] = temp[:, [j, i]]
    else:
        for i, j in col_swaps:
            temp[:, [i, j]] = temp[:, [j, i]]
        for i, j in row_swaps:
            temp[[i, j], :] = temp[[j, i], :]
    return temp

def reverse_permutation(matrix, row_swaps, col_swaps, order):
    temp = matrix.copy()
    if order[0] == "row":
        for i, j in reversed(col_swaps):
            temp[:, [i, j]] = temp[:, [j, i]]
        for i, j in reversed(row_swaps):
            temp[[i, j], :] = temp[[j, i], :]
    else:
        for i, j in reversed(row_swaps):
            temp[[i, j], :] = temp[[j, i], :]
        for i, j in reversed(col_swaps):
            temp[:, [i, j]] = temp[:, [j, i]]
    return temp

def apply_modular_operations(matrix, subkey, mod_op, transpose=False):
    temp_m = matrix.astype(np.uint16)
    temp_s = subkey.T.astype(np.uint16) if transpose else subkey.astype(np.uint16)
    if mod_op == "add":
        return ((temp_m + temp_s) % 256).astype(np.uint8)
    else:
        return ((temp_m - temp_s) % 256).astype(np.uint8)

def determine_operation_sequence(seed1):
    rng = random.Random(seed1)
    operations = OPERATIONS.copy()
    rng.shuffle(operations)
    return operations

def determine_sub_operations(seed2):
    rng = random.Random(seed2)
    row_swaps = [(rng.randint(0, MATRIX_SIZE - 1), rng.randint(0, MATRIX_SIZE - 1)) for _ in range(SWAP_COUNT)]
    col_swaps = [(rng.randint(0, MATRIX_SIZE - 1), rng.randint(0, MATRIX_SIZE - 1)) for _ in range(SWAP_COUNT)]
    mod_order = MOD_ORDER.copy()
    permutation_order = PERMUTATION_ORDER.copy()
    rng.shuffle(mod_order)
    rng.shuffle(permutation_order)
    return row_swaps, col_swaps, permutation_order, mod_order

def pack_header(last_block_size, rsa_enc_key=None):
    """
    Builds the binary header:
    - 1 byte: rsa_flag (0 or 1)
    - If rsa_flag: 4 bytes key_size (uint32) + encrypted_key
    - 8 bytes: last_block_size (uint64)
    """
    buf = bytearray()
    rsa_flag = bool(rsa_enc_key)
    buf.extend(struct.pack("B", rsa_flag))
    if rsa_flag:
        buf.extend(struct.pack("I", len(rsa_enc_key)))
        buf.extend(rsa_enc_key)
    buf.extend(struct.pack("Q", last_block_size))
    return bytes(buf)

def unpack_header(data_stream):
    """
    Reads the binary header from a bytes stream.
    Returns: (rsa_flag, rsa_enc_key, last_block_size, header_size)
    """
    start_pos = data_stream.tell()
    raw_flag = data_stream.read(1)
    if not raw_flag:
        raise ValueError("File is empty or not a valid Enigmatrix (.emx) file.")
    try:
        rsa_flag = struct.unpack("B", raw_flag)[0]
        rsa_enc_key = None
        if rsa_flag:
            key_size_bytes = data_stream.read(4)
            if len(key_size_bytes) < 4:
                raise ValueError("Corrupted .emx file header (invalid RSA metadata).")
            key_size = struct.unpack("I", key_size_bytes)[0]
            rsa_enc_key = data_stream.read(key_size)
            if len(rsa_enc_key) < key_size:
                raise ValueError("Corrupted .emx file header (incomplete RSA key).")
        last_block_bytes = data_stream.read(8)
        if len(last_block_bytes) < 8:
            raise ValueError("Corrupted .emx file header (missing block metadata).")
        last_block_size = struct.unpack("Q", last_block_bytes)[0]
        header_size = data_stream.tell() - start_pos
        return rsa_flag, rsa_enc_key, last_block_size, header_size
    except struct.error:
        raise ValueError("Invalid or corrupted Enigmatrix (.emx) file format.")

def encrypt_bytes(data: bytes, raw_key: str, public_key_pem: str = None, progress_cb = None) -> bytes:
    """
    Encrypts byte buffer using Enigmatrix cipher and optional RSA public key.
    """
    if isinstance(raw_key, str):
        raw_key = raw_key.encode('utf-8')
    if len(raw_key) < 4:
        raise ValueError("Key must be at least 4 characters long")

    data_size = len(data)
    num_blocks = (data_size // BLOCK_SIZE) + (1 if data_size % BLOCK_SIZE > 0 or data_size == 0 else 0)
    last_block_size = data_size % BLOCK_SIZE if data_size > 0 else 0

    primary_hash = key_utils.primary_hash(raw_key)
    seed1, seed2 = key_utils.extract_prng_seeds(primary_hash)

    rsa_enc_key = None
    if public_key_pem:
        rsa_enc_key = key_utils.rsa_encrypt_key(raw_key, public_key_pem)

    header = pack_header(last_block_size, rsa_enc_key)
    op_order = determine_operation_sequence(seed1)
    row_swaps, col_swaps, permutation_order, mod_order = determine_sub_operations(seed2)

    out_stream = io.BytesIO()
    out_stream.write(header)

    in_stream = io.BytesIO(data)

    for i in range(num_blocks):
        block = in_stream.read(BLOCK_SIZE)
        if len(block) < BLOCK_SIZE:
            block = pad_block(block)

        block_matrix = bytes_to_matrix(block)
        subkey = key_utils.derive_subkey(primary_hash, raw_key, i)
        subkey_matrix = bytes_to_matrix(subkey)

        for op in op_order:
            if op == "xor":
                block_matrix = apply_xor(block_matrix, subkey_matrix)
            elif op == "modular":
                for t, mod_op in enumerate(mod_order):
                    block_matrix = apply_modular_operations(block_matrix, subkey_matrix, mod_op, t == 1)
            elif op == "permutation":
                block_matrix = apply_permutation(block_matrix, row_swaps, col_swaps, permutation_order)

        out_stream.write(matrix_to_bytes(block_matrix))

        if progress_cb:
            progress_cb(int(((i + 1) / num_blocks) * 100), i + 1, num_blocks)

    return out_stream.getvalue()

def decrypt_bytes(data: bytes, raw_key: str = None, private_key_pem: str = None, progress_cb = None) -> bytes:
    """
    Decrypts byte buffer using Enigmatrix cipher and key/RSA private key.
    """
    in_stream = io.BytesIO(data)
    rsa_flag, rsa_enc_key, last_block_size, header_size = unpack_header(in_stream)

    if rsa_flag:
        if not private_key_pem:
            raise ValueError("File was encrypted with an RSA public key. An RSA private key is required to decrypt.")
        try:
            raw_key = key_utils.rsa_decrypt_key(rsa_enc_key, private_key_pem)
        except Exception as e:
            raise ValueError(f"Failed to decrypt RSA session key: {str(e)}")
    else:
        if not raw_key:
            raise ValueError("Encryption key is required to decrypt this file")
        if isinstance(raw_key, str):
            raw_key = raw_key.encode('utf-8')

    total_enc_size = len(data) - header_size
    if total_enc_size <= 0 or total_enc_size % BLOCK_SIZE != 0:
        raise ValueError("Invalid file structure: The file is not a valid Enigmatrix (.emx) encrypted file.")
    num_blocks = (total_enc_size // BLOCK_SIZE)

    primary_hash = key_utils.primary_hash(raw_key)
    seed1, seed2 = key_utils.extract_prng_seeds(primary_hash)

    op_order = determine_operation_sequence(seed1)
    row_swaps, col_swaps, permutation_order, mod_order = determine_sub_operations(seed2)

    out_stream = io.BytesIO()

    for i in range(num_blocks):
        block = in_stream.read(BLOCK_SIZE)
        if len(block) != BLOCK_SIZE:
            break

        block_matrix = bytes_to_matrix(block)
        subkey = key_utils.derive_subkey(primary_hash, raw_key, i)
        subkey_matrix = bytes_to_matrix(subkey)

        for op in reversed(op_order):
            if op == "permutation":
                block_matrix = reverse_permutation(block_matrix, row_swaps, col_swaps, permutation_order)
            elif op == "modular":
                for t, mod_op in enumerate(mod_order):
                    block_matrix = apply_modular_operations(block_matrix, subkey_matrix, mod_op, t == 0)
            elif op == "xor":
                block_matrix = apply_xor(block_matrix, subkey_matrix)

        decrypted_block = matrix_to_bytes(block_matrix)
        if i == num_blocks - 1 and last_block_size > 0:
            decrypted_block = truncate_block(decrypted_block, last_block_size)

        out_stream.write(decrypted_block)

        if progress_cb:
            progress_cb(int(((i + 1) / num_blocks) * 100), i + 1, num_blocks)

    return out_stream.getvalue()
