from app.core.security import hash_password, verify_password


def test_hash_password_uses_argon2() -> None:
    hashed_password = hash_password("correct horse battery staple")

    assert hashed_password.startswith("$argon2")
    assert hashed_password != "correct horse battery staple"


def test_verify_password_checks_argon2_hash() -> None:
    hashed_password = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", hashed_password) is True
    assert verify_password("wrong password", hashed_password) is False
