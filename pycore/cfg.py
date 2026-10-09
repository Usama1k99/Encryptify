# Configuration for Enigmatrix Core
VERSION = "3.0.0"
BLOCK_SIZE = 1024 * 1024  # 1 MB
RSA_KEY_SIZE = 4096
SWAP_COUNT = 512
MATRIX_SIZE = 1024
MIN_KEY_LEN = 4

# Signatures for Steganos & PicIt
STEG_SIGNATURE_TEXT = "Signature-Text-To-Be-Used-In-Steganos-To-Detect-Encoding"
STEG_PREFIX_TEXT = "Steganos-Prefix-Text"
PICIT_SIGNATURE_TEXT = "PicIt-Signature-Text-To-Insert-With-Text-And-To-Check-Correctness-Of-The-Key"
