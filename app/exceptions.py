class VaultError(Exception):
    pass


class VaultNotFoundError(VaultError):
    pass


class InvalidShareError(VaultError):
    pass


class WrongPasswordError(VaultError):
    pass


class IntegrityError(VaultError):
    pass