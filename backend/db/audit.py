import json
import re
from datetime import datetime
from typing import Any, List, Optional
from sqlalchemy.orm import Session
from .models import AuditLog

# PII Masking regular expressions
CARD_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
PHONE_PATTERN = re.compile(r'(?:\+91[\-\s]?)?[6-9](?:[\d\-\s]){8,11}\d\b')
EMAIL_PATTERN = re.compile(r'\b([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b')
OTP_PIN_CVV_PATTERN = re.compile(r'\b(?:otp|pin|cvv|cvv2|password)\s*[:=]?\s*([0-9a-zA-Z]{3,8})\b', re.IGNORECASE)

def mask_pii_string(text: str) -> str:
    """Replaces sensitive PII patterns with secure masked placeholders."""
    if not text:
        return text

    # Mask card numbers (preserve last 4)
    def mask_card(m):
        raw = re.sub(r'[\s-]', '', m.group(0))
        if len(raw) >= 12:
            return f"****-****-****-{raw[-4:]}"
        return "****-CARD"

    # Mask phone numbers (preserve last 3)
    def mask_phone(m):
        raw = m.group(0)
        digits = re.sub(r'\D', '', raw)
        if len(digits) >= 10:
            return f"+91-*****{digits[-3:]}"
        return "+91-**********"

    # Mask emails
    def mask_email(m):
        first = m.group(1)
        domain = m.group(2)
        return f"{first}***{domain}"

    # Redact any accidental OTP/PIN in text
    def mask_otp(m):
        return "OTP/PIN: [REDACTED_SECURITY_DATA]"

    masked = OTP_PIN_CVV_PATTERN.sub(mask_otp, text)
    masked = CARD_PATTERN.sub(mask_card, masked)
    masked = PHONE_PATTERN.sub(mask_phone, masked)
    masked = EMAIL_PATTERN.sub(mask_email, masked)
    return masked

def mask_pii_data(data: Any) -> Any:
    """Recursively traverses dictionaries, lists, and primitives to mask PII."""
    if isinstance(data, str):
        return mask_pii_string(data)
    elif isinstance(data, dict):
        masked_dict = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(term in k_lower for term in ("otp", "pin", "cvv", "password", "secret")):
                masked_dict[k] = "[REDACTED_CREDENTIAL]"
            elif "phone" in k_lower and isinstance(v, str):
                masked_dict[k] = mask_pii_string(v)
            elif "card" in k_lower and isinstance(v, str):
                masked_dict[k] = mask_pii_string(v)
            else:
                masked_dict[k] = mask_pii_data(v)
        return masked_dict
    elif isinstance(data, list):
        return [mask_pii_data(item) for item in data]
    return data

def log_audit_event(
    db: Session,
    actor: str,
    action: str,
    case_id: Optional[str] = None,
    txn_id: Optional[str] = None,
    input_payload: Optional[Any] = None,
    output_payload: Optional[Any] = None,
    decision_reason: Optional[str] = None,
    policy_citations: Optional[List[str]] = None
) -> AuditLog:
    """
    Appends an immutable audit entry with strict PII masking.
    Non-negotiable rule 6: Every step writes to an immutable audit log.
    """
    safe_input = None
    if input_payload is not None:
        safe_input = json.dumps(mask_pii_data(input_payload), default=str)

    safe_output = None
    if output_payload is not None:
        safe_output = json.dumps(mask_pii_data(output_payload), default=str)

    citations_json = None
    if policy_citations:
        citations_json = json.dumps(policy_citations)

    entry = AuditLog(
        timestamp=datetime.utcnow(),
        case_id=case_id,
        txn_id=txn_id,
        actor=actor,
        action=action,
        input_payload=safe_input,
        output_payload=safe_output,
        decision_reason=decision_reason,
        policy_citations=citations_json
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
