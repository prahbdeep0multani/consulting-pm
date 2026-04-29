from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return str(_ctx.hash(password))


def verify_password(plain: str, hashed: str) -> bool:
    return bool(_ctx.verify(plain, hashed))
