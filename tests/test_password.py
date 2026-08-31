from app.services.password import hash_password, verify_password


def test_hash_and_verify():
    h = hash_password("secret12")
    assert h != "secret12"
    assert verify_password("secret12", h)
    assert not verify_password("wrong", h)
