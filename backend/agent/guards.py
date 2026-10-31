import re
from typing import Tuple
from backend.db.audit import mask_pii_string, mask_pii_data

# Forbidden security phrases that an AI agent or output must NEVER ask for
FORBIDDEN_REQUEST_PATTERNS = [
    re.compile(r'\b(enter|provide|share|tell|send|give|what is|verify)\b.*?\b(otp|one[- ]time[- ]password|pin|upi[- ]pin|atm[- ]pin|cvv|cvc|card number)\b', re.IGNORECASE),
    re.compile(r'\b(otp|pin|cvv|cvc)\b.*?\b(needed|required|verification|confirm)\b', re.IGNORECASE),
    re.compile(r'\b(16[- ]digit|card digits|cvv2)\b', re.IGNORECASE),
]

class SecurityOutputGuardViolation(Exception):
    """Raised when an AI output attempts to solicit sensitive credentials."""
    pass

class OutputGuard:
    """
    Non-negotiable Design Rule 4:
    Never ask for OTP, PIN, CVV or full card number.
    Add an output guard that blocks any reply asking for these.
    """

    @classmethod
    def sanitize_and_validate(cls, message_text: str) -> Tuple[bool, str]:
        """
        Inspects outgoing customer message.
        Returns (is_safe, sanitized_or_fallback_message).
        If violation detected, flags is_safe=False and replaces text.
        """
        if not message_text:
            return True, message_text

        for pattern in FORBIDDEN_REQUEST_PATTERNS:
            if pattern.search(message_text):
                # Critical violation: Replace immediately with safety-compliant message
                safe_text = (
                    "Security Notice: Saarthi will never ask for your OTP, PIN, CVV, or card details. "
                    "Our systems verify all transaction states directly with the banking switch."
                )
                return False, safe_text

        # Mask any accidental PII in message
        sanitized = mask_pii_string(message_text)
        return True, sanitized

    @classmethod
    def sanitize_context_for_llm(cls, context_text: str) -> str:
        """
        Masks customer PII (phone, email, cards, account numbers) before
        passing into the LLM context.
        """
        return mask_pii_string(context_text)

