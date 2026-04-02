from app.core.security import decode_token_payload, verify_token

def test_decode_token_payload_exception():
    assert decode_token_payload("invalid-token", "access") is None

def test_verify_token_exception():
    assert verify_token("invalid-token", "access") is None
