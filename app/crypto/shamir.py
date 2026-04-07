from __future__ import annotations

import secrets
from typing import List, Sequence, Tuple

# Большое простое число.
# Оно больше любого 256-битного ключа, поэтому подходит для secret sharing.
PRIME = 2**521 - 1

Share = Tuple[int, int]


def _bytes_to_int(data: bytes) -> int:
    return int.from_bytes(data, byteorder="big")


def _int_to_bytes(value: int, length: int) -> bytes:
    return value.to_bytes(length, byteorder="big")


def _eval_polynomial(coeffs: Sequence[int], x: int, prime: int) -> int:
    """
    Вычисляет значение полинома в точке x:
    a0 + a1*x + a2*x^2 + ...
    """
    result = 0
    power = 1

    for coeff in coeffs:
        result = (result + coeff * power) % prime
        power = (power * x) % prime

    return result


def split_secret(secret: bytes, n: int, k: int) -> List[Share]:
    """
    Делит secret на n долей так, чтобы для восстановления нужно было минимум k долей.
    Возвращает список пар (x, y).
    """
    if not secret:
        raise ValueError("Secret must not be empty")

    if not (2 <= k <= n):
        raise ValueError("Require 2 <= k <= n")

    secret_int = _bytes_to_int(secret)

    if secret_int >= PRIME:
        raise ValueError("Secret is too large for the chosen field")

    # a0 = secret, остальные коэффициенты случайные
    coeffs = [secret_int] + [secrets.randbelow(PRIME) for _ in range(k - 1)]

    shares: List[Share] = []
    for x in range(1, n + 1):
        y = _eval_polynomial(coeffs, x, PRIME)
        shares.append((x, y))

    return shares


def _lagrange_interpolate_zero(shares: Sequence[Share], prime: int) -> int:
    """
    Восстанавливает значение полинома в точке 0 по методу Лагранжа.
    """
    secret = 0

    for i, (x_i, y_i) in enumerate(shares):
        numerator = 1
        denominator = 1

        for j, (x_j, _) in enumerate(shares):
            if i == j:
                continue
            numerator = (numerator * (-x_j)) % prime
            denominator = (denominator * (x_i - x_j)) % prime

        # Обратный элемент по модулю prime
        lagrange_coeff = numerator * pow(denominator, -1, prime)
        secret = (prime + secret + (y_i * lagrange_coeff)) % prime

    return secret


def reconstruct_secret(shares: Sequence[Share], secret_length: int) -> bytes:
    """
    Восстанавливает secret по любому набору из k или более долей.
    secret_length нужен, чтобы вернуть исходную длину байтов.
    """
    if secret_length <= 0:
        raise ValueError("secret_length must be positive")

    if len(shares) < 2:
        raise ValueError("At least 2 shares are required")

    # Проверка на дубликаты x
    xs = [x for x, _ in shares]
    if len(xs) != len(set(xs)):
        raise ValueError("Duplicate share indexes found")

    secret_int = _lagrange_interpolate_zero(shares, PRIME)
    return _int_to_bytes(secret_int, secret_length)