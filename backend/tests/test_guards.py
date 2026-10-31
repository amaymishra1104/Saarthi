import pytest
from backend.agent.guards import OutputGuard
from backend.db.audit import mask_pii_string, mask_pii_data

def test_output_guard_blocks_otp_requests():
    prompt = "Please share your OTP so I can process your refund."
    is_safe, sanitized = OutputGuard.sanitize_and_validate(prompt)
    assert is_safe is False
    assert "will never ask for your OTP" in sanitized
    assert "share your OTP" not in sanitized

def test_output_guard_blocks_pin_and_cvv():
    for term in ["enter your ATM PIN", "provide CVV", "tell me your UPI PIN", "verify 16-digit card number"]:
        msg = f"In order to proceed, please {term}."
        is_safe, sanitized = OutputGuard.sanitize_and_validate(msg)
        assert is_safe is False
        assert "Security Notice" in sanitized

def test_output_guard_allows_safe_messages():
    safe_msg = "Your refund of ₹2,000 has been verified and processed with reference REV-882910."
    is_safe, sanitized = OutputGuard.sanitize_and_validate(safe_msg)
    assert is_safe is True
    assert sanitized == safe_msg

def test_pii_masking_phone_and_cards():
    text = "Customer phone is +91 98765 43210 and card number is 4111 2222 3333 4444."
    masked = mask_pii_string(text)
    assert "98765" not in masked
    assert "4111 2222" not in masked
    assert "****-****-****-4444" in masked

def test_pii_masking_nested_data():
    data = {
        "customer": {"phone": "+91 9911223344", "email": "aarav.sharma@gmail.com"},
        "details": ["card: 5500 0000 1111 2222", "amount: 500"]
    }
    masked = mask_pii_data(data)
    assert "aarav.sharma@gmail.com" not in json_str(masked)
    assert "5500" not in json_str(masked)

def json_str(d):
    import json
    return json.dumps(d)

