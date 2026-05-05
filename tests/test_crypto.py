"""
test_crypto.py — Kiểm tra module mã hóa cho cả Jetson Nano và Orchestrator.

Chạy ở cả 2 phía với cùng WORKER_ENCRYPTION_KEY / PAYLOAD_ENCRYPTION_KEY:

  # Jetson Nano (Python 3.6):
  WORKER_ENCRYPTION_KEY=ij0zznD2P2kNZKCYX7rfa993jrjDNSLQZI4aWush5Fo= python3 tests/test_crypto.py

  # Orchestrator (Python 3.10+):
  PAYLOAD_ENCRYPTION_KEY=ij0zznD2P2kNZKCYX7rfa993jrjDNSLQZI4aWush5Fo= python tests/test_crypto.py
"""

import os
import sys

# --- Setup key for test ---
# Ưu tiên đọc từ env, nếu không có thì dùng key mẫu để test
TEST_KEY = (
    os.environ.get("WORKER_ENCRYPTION_KEY")
    or os.environ.get("PAYLOAD_ENCRYPTION_KEY")
    or "ij0zznD2P2kNZKCYX7rfa993jrjDNSLQZI4aWush5Fo="
)
os.environ["WORKER_ENCRYPTION_KEY"] = TEST_KEY
os.environ["PAYLOAD_ENCRYPTION_KEY"] = TEST_KEY

print("=" * 60)
print("Fingerprint Crypto Utils -- Integration Test")
print("Python version:", sys.version)
print("Key (first 10 chars):", TEST_KEY[:10] + "...")
print("=" * 60)

# --- Import module ---
try:
    from app.core.crypto_utils import (
        encrypt_image_bytes,
        decrypt_image_bytes,
        encrypt_field,
        decrypt_field,
        is_encryption_enabled,
        reset_fernet,
    )
    print("[OK] Import app.core.crypto_utils")
except ImportError as e:
    print("[FAIL] Import error:", e)
    sys.exit(1)

# --- Test 1: is_encryption_enabled ---
assert is_encryption_enabled(), "FAIL: is_encryption_enabled() returned False"
print("[OK] is_encryption_enabled() = True")

# --- Test 2: Encrypt / Decrypt image bytes ---
fake_image = b"TIFF\x00\x01\x02\x03FINGERPRINT_DATA_SAMPLE" * 200
encrypted = encrypt_image_bytes(fake_image)
assert isinstance(encrypted, str), "FAIL: encrypted should be str"
assert encrypted != fake_image.decode("latin-1", errors="ignore"), "FAIL: encryption not applied"
print("[OK] encrypt_image_bytes: %d bytes -> %d chars" % (len(fake_image), len(encrypted)))

decrypted = decrypt_image_bytes(encrypted)
assert decrypted == fake_image, "FAIL: decrypted != original"
print("[OK] decrypt_image_bytes: round-trip OK")

# --- Test 3: Encrypt / Decrypt text field (e.g. embedding JSON) ---
import json
embedding = [0.123, 0.456, 0.789, -0.111] * 64  # 256-dim vector
embedding_json = json.dumps(embedding)
enc_field = encrypt_field(embedding_json)
assert isinstance(enc_field, str), "FAIL: encrypted field should be str"

dec_field = decrypt_field(enc_field)
assert dec_field == embedding_json, "FAIL: decrypted field != original"
restored_vector = json.loads(dec_field)
assert restored_vector == embedding, "FAIL: restored vector != original"
print("[OK] encrypt_field / decrypt_field: embedding round-trip OK")

# --- Test 4: Different encryptions produce different ciphertexts (nonce randomness) ---
enc1 = encrypt_image_bytes(fake_image)
enc2 = encrypt_image_bytes(fake_image)
assert enc1 != enc2, "FAIL: same plaintext should produce different ciphertexts (Fernet uses random IV)"
print("[OK] Nonce randomness: each encryption is unique")

# --- Test 5: Tampered token is rejected ---
tampered = encrypted[:-5] + "XXXXX"
try:
    decrypt_image_bytes(tampered)
    print("[FAIL] Should have raised InvalidToken for tampered ciphertext")
    sys.exit(1)
except Exception:
    print("[OK] Tampered token correctly rejected (InvalidToken)")

# --- Test 6: Wrong key is rejected ---
reset_fernet()
os.environ["WORKER_ENCRYPTION_KEY"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
os.environ["PAYLOAD_ENCRYPTION_KEY"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
try:
    decrypt_image_bytes(encrypted)
    print("[FAIL] Should have raised InvalidToken for wrong key")
    sys.exit(1)
except Exception:
    print("[OK] Wrong key correctly rejected (InvalidToken)")

# Restore key
reset_fernet()
os.environ["WORKER_ENCRYPTION_KEY"] = TEST_KEY
os.environ["PAYLOAD_ENCRYPTION_KEY"] = TEST_KEY

# --- Done ---
print()
print("=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
