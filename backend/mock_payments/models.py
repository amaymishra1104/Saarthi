from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class MockTransaction(BaseModel):
    txn_id: str
    amount: float
    currency: str = "INR"
    customer_id: str
    customer_name: str
    customer_phone: str
    merchant: str
    timestamp: datetime
    status: str  # SUCCESS, FAILED, PENDING_CONFIRMATION, REVERSAL_PENDING, REVERSED, DUPLICATE_DEBIT, FLAGGED_RISK
    status_source: str  # CORE_SWITCH, NPCI_UPI, ACQUIRER_GATEWAY, BANK_NETWORK
    debit_confirmed: bool
    credit_confirmed: bool
    risk_flags: List[str] = Field(default_factory=list)
    reversal_eligible: bool = False
    reversal_ref: Optional[str] = None
    notes: Optional[str] = None

class ReversalRequest(BaseModel):
    reason: str
    requested_by: str = "SAARTHI_AGENT"

class ReversalResponse(BaseModel):
    success: bool
    txn_id: str
    reversal_ref: str
    status: str
    message: str
    timestamp: datetime

class MockCasePayload(BaseModel):
    case_id: str
    txn_id: Optional[str] = None
    customer_id: str
    status: str
    summary: str

class ChaosConfig(BaseModel):
    lookup_fail: bool = False
    api_timeout: bool = False
    ambiguous_status: bool = False
    duplicate_attempt: bool = False
    verification_mismatch: bool = False

