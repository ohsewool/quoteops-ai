from pwdlib import PasswordHash

_PASSWORD_HASH = PasswordHash.recommended()


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    return _PASSWORD_HASH.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _PASSWORD_HASH.verify(password, password_hash)
