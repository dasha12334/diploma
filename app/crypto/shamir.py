from __future__ import annotations

import secrets
from typing import List, Sequence, Tuple

PRIME = 2**521 - 1
Share = Tuple[int, int]

def _bytes_to_int(data: bytes) -> int:
    return int.from_bytes(data, byteorder="big")

def _int_to_bytes(value: int, length: int) -> bytes:
    return value.to_bytes(length, byteorder="big")

def _eval_polynomial(coeffs: Sequence[int], x: int, prime: int) -> int:
    result = 0
    power = 1

    for coeff in coeffs:
        result = (result + coeff * power) % prime
        power = (power * x) % prime

    return result

def split_secret(secret: bytes, n: int, k: int) -> List[Share]:

    if not secret:
        raise ValueError("Secret must not be empty")

    if not (2 <= k <= n):
        raise ValueError("Require 2 <= k <= n")

    secret_int = _bytes_to_int(secret)

    if secret_int >= PRIME:
        raise ValueError("Secret is too large for the chosen field")

    coeffs = [secret_int] + [secrets.randbelow(PRIME) for _ in range(k - 1)]

    shares: List[Share] = []
    for x in range(1, n + 1):
        y = _eval_polynomial(coeffs, x, PRIME)
        shares.append((x, y))

    return shares

def _lagrange_interpolate_zero(shares: Sequence[Share], prime: int) -> int:

    secret = 0

    for i, (x_i, y_i) in enumerate(shares):
        numerator = 1
        denominator = 1

        for j, (x_j, _) in enumerate(shares):
            if i == j:
                continue
            numerator = (numerator * (-x_j)) % prime
            denominator = (denominator * (x_i - x_j)) % prime

        lagrange_coeff = numerator * pow(denominator, -1, prime)
        secret = (prime + secret + (y_i * lagrange_coeff)) % prime

    return secret

def reconstruct_secret(shares: Sequence[Share], secret_length: int) -> bytes:

    if secret_length <= 0:
        raise ValueError("secret_length must be positive")

    if len(shares) < 2:
        raise ValueError("At least 2 shares are required")

    xs = [x for x, _ in shares]
    if len(xs) != len(set(xs)):
        raise ValueError("Duplicate share indexes found")

    secret_int = _lagrange_interpolate_zero(shares, PRIME)
    return _int_to_bytes(secret_int, secret_length)

def verify_shares(shares: Sequence[Share], k: int, prime: int = PRIME) -> bool:
    if len(shares) < k:
        return False

    xs = [x for x, _ in shares]
    if len(xs) != len(set(xs)):
        return False

    test_shares = shares[:k]

    for i in range(k, len(shares)):
        x_i, y_i = shares[i]

        expected_y = 0
        for j, (x_j, y_j) in enumerate(test_shares):
            numerator = 1
            denominator = 1

            for m, (x_m, _) in enumerate(test_shares):
                if m == j:
                    continue
                numerator = (numerator * (x_i - x_m)) % prime
                denominator = (denominator * (x_j - x_m)) % prime

            lagrange_coeff = numerator * pow(denominator, -1, prime)
            expected_y = (expected_y + y_j * lagrange_coeff) % prime

        if expected_y != y_i:
            return False

    return True