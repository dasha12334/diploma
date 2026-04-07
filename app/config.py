import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "vault.db")

DEFAULT_N = 5
DEFAULT_K = 3

KEY_SIZE = 32          # 256 бит
SALT_SIZE = 16
NONCE_SIZE = 12

KDF_ITERATIONS = 100_000