from app.services.auth_tokens import create_access_token, decode_token


def test_roundtrip():
    tok = create_access_token("uid-1", "a@b.com", secret="s", hours=72)
    claims = decode_token(tok, secret="s")
    assert claims["user_id"] == "uid-1"
    assert claims["email"] == "a@b.com"
