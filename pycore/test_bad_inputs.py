import unittest
from pycore import text_engine, image_engine, enigmatrix

class TestBadInputs(unittest.TestCase):
    def test_empty_inputs(self):
        # Empty text
        with self.assertRaises(ValueError) as ctx:
            text_engine.process_text("", "key", "encrypt", "vigenere")
        self.assertIn("Please enter some text", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            text_engine.process_text("   ", "key", "decrypt", "vigenere")
        self.assertIn("Please enter some text", str(ctx.exception))

    def test_missing_key(self):
        for algo in ["vigenere", "scramble", "xor"]:
            with self.assertRaises(ValueError) as ctx:
                text_engine.process_text("Sample message", "", "encrypt", algo)
            self.assertIn("Please provide an encryption key", str(ctx.exception))

            with self.assertRaises(ValueError) as ctx:
                text_engine.process_text("Sample message", "   ", "decrypt", algo)
            self.assertIn("Please provide an encryption key", str(ctx.exception))

    def test_binary_bad_inputs(self):
        # Non-binary characters
        with self.assertRaises(ValueError) as ctx:
            text_engine.process_text("Hello World", "", "decrypt", "binary")
        self.assertIn("Binary text can only contain 0s and 1s", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            text_engine.process_text("01010101 01010102", "", "decrypt", "binary")
        self.assertIn("Binary text can only contain 0s and 1s", str(ctx.exception))

        # Incomplete bits
        with self.assertRaises(ValueError) as ctx:
            text_engine.process_text("0101010", "", "decrypt", "binary")
        self.assertIn("Incomplete binary sequence", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            text_engine.process_text("01010101 010", "", "decrypt", "binary")
        self.assertIn("Incomplete binary sequence", str(ctx.exception))

        # Empty or spaces only
        with self.assertRaises(ValueError) as ctx:
            text_engine.process_text("    ", "", "decrypt", "binary")
        self.assertIn("Please enter binary text", str(ctx.exception))

    def test_binary_valid_variations(self):
        # Formatted with spaces, tabs, newlines
        bin_str = "01001000\n01101001\t00100001"
        res = text_engine.process_text(bin_str, "", "decrypt", "binary")
        self.assertEqual(res, "Hi!")

    def test_enigmatrix_bad_inputs(self):
        # Key too short
        with self.assertRaises(ValueError) as ctx:
            enigmatrix.encrypt_bytes(b"some data", "123")
        self.assertIn("at least 4 characters", str(ctx.exception))

        # Corrupt file header / too short to be an emx file
        with self.assertRaises(Exception):
            enigmatrix.decrypt_bytes(b"short", "password123")

        with self.assertRaises(Exception):
            enigmatrix.decrypt_bytes(b"\x00" * 4, "password123")

if __name__ == "__main__":
    unittest.main()
