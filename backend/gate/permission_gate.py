from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.config import settings
from backend.db.models import IdempotencyRecord

class GateDecision(BaseModel):
    decision: str  # ALLOW, REQUIRE_APPROVAL, DENY
    reason_code: str
    reason_detail: str
    policy_citations: List[str]
    allowed: bool
    requires_approval: bool
    is_denied: bool

class DeterministicPermissionGate:
    """
    Non-negotiable Design Rule 1 & 6:
    Plain Python deterministic Permission Gate.
    The LLM NEVER decides execution. Application code enforces:
    - Customer Authentication (app session, never OTP/PIN)
    - Idempotency in DB
    - Transaction State confirmation & eligibility
    - Risk flags
    - Financial Limits (Tier 1 <= 5k, Tier 2 > 5k require approval)
    """

    def evaluate(
        self,
        proposed_action: str,
        txn_data: Dict[str, Any],
        customer_auth: Dict[str, Any],
        idempotency_key: str,
        db: Session,
        is_supervisor_approved: bool = False
    ) -> GateDecision:
        citations = []

        # 1. Customer Authentication Check
        if not customer_auth.get("authenticated", False):
            return GateDecision(
                decision="DENY",
                reason_code="AUTH_UNVERIFIED",
                reason_detail="Customer session is not authenticated via trusted app token. Never ask for OTP/PIN.",
                policy_citations=["[POL-ESC-005: Rule ESC-1 (escalation_and_risk.md)]"],
                allowed=False,
                requires_approval=False,
                is_denied=True
            )

        auth_cust_id = customer_auth.get("customer_id")
        txn_cust_id = txn_data.get("customer_id")
        if auth_cust_id and txn_cust_id and auth_cust_id.lower() != txn_cust_id.lower():
            return GateDecision(
                decision="DENY",
                reason_code="IDENTITY_MISMATCH",
                reason_detail=f"Authenticated customer {auth_cust_id} does not own transaction {txn_data.get('txn_id')}.",
                policy_citations=["[POL-ESC-005: Rule ESC-1 (escalation_and_risk.md)]"],
                allowed=False,
                requires_approval=False,
                is_denied=True
            )

        # 2. Idempotency Check in DB
        txn_id = txn_data.get("txn_id", "")
        existing_idempotency = db.query(IdempotencyRecord).filter(
            (IdempotencyRecord.idempotency_key == idempotency_key) |
            ((IdempotencyRecord.action_type == proposed_action) & (IdempotencyRecord.txn_id == txn_id))
        ).first()

        if existing_idempotency:
            citations.append("[POL-FPR-001: Rule FPR-4 (failed_payment_reversal.md)]")
            return GateDecision(
                decision="DENY",
                reason_code="IDEMPOTENCY_VIOLATION",
                reason_detail=f"Action '{proposed_action}' on transaction {txn_id} was already executed (Key: {existing_idempotency.idempotency_key}). Duplicate action blocked.",
                policy_citations=citations,
                allowed=False,
                requires_approval=False,
                is_denied=True
            )

        # 3. Risk Flags Check
        risk_flags = txn_data.get("risk_flags") or []
        if risk_flags:
            citations.append("[POL-ESC-005: Rule ESC-2 (escalation_and_risk.md)]")
            return GateDecision(
                decision="DENY",
                reason_code="RISK_FLAG_DETECTED",
                reason_detail=f"Active security risk flags detected on transaction: {', '.join(risk_flags)}. Autonomous execution prohibited.",
                policy_citations=citations,
                allowed=False,
                requires_approval=False,
                is_denied=True
            )

        # 4. Status and Eligibility Check for Financial Reversal
        if proposed_action == "initiate_reversal":
            citations.append("[POL-FPR-001: Rule FPR-1 (failed_payment_reversal.md)]")
            status = txn_data.get("status")

            if status == "PENDING_CONFIRMATION":
                citations.append("[POL-PSH-002: Rule PSH-1 (pending_status_handling.md)]")
                citations.append("[POL-PSH-002: Rule PSH-4 (pending_status_handling.md)]")
                return GateDecision(
                    decision="DENY",
                    reason_code="UNCONFIRMED_PENDING_STATUS",
                    reason_detail="Transaction is in PENDING_CONFIRMATION. Financial action forbidden until authoritative clearing settles. I cannot call it failed or successful yet.",
                    policy_citations=citations,
                    allowed=False,
                    requires_approval=False,
                    is_denied=True
                )

            valid_states = ("FAILED", "DUPLICATE_DEBIT")
            if status not in valid_states:
                return GateDecision(
                    decision="DENY",
                    reason_code="INVALID_STATE_FOR_REVERSAL",
                    reason_detail=f"Transaction status '{status}' is not eligible for reversal. Must be confirmed FAILED or DUPLICATE_DEBIT.",
                    policy_citations=citations,
                    allowed=False,
                    requires_approval=False,
                    is_denied=True
                )

            if not txn_data.get("debit_confirmed", False):
                return GateDecision(
                    decision="DENY",
                    reason_code="DEBIT_NOT_CONFIRMED",
                    reason_detail="Customer bank account debit was never confirmed by issuing bank.",
                    policy_citations=citations,
                    allowed=False,
                    requires_approval=False,
                    is_denied=True
                )

            if txn_data.get("credit_confirmed", False):
                return GateDecision(
                    decision="DENY",
                    reason_code="MERCHANT_CREDIT_CONFIRMED",
                    reason_detail="Merchant order was already credited; refund must go through merchant return flow, not core reversal.",
                    policy_citations=citations,
                    allowed=False,
                    requires_approval=False,
                    is_denied=True
                )

            # 5. Amount Limit & Supervisory Authorization Tier Check
            amount = float(txn_data.get("amount", 0.0))
            citations.append("[POL-LMT-006: Rule LMT-1 (action_limits.md)]")

            if amount > 50000.0:
                return GateDecision(
                    decision="DENY",
                    reason_code="TIER3_MANUAL_OPS_ONLY",
                    reason_detail=f"Amount INR {amount:,.2f} exceeds ₹50,000 threshold. Strictly restricted to manual payments operations team.",
                    policy_citations=citations,
                    allowed=False,
                    requires_approval=False,
                    is_denied=True
                )

            if amount > settings.AUTO_ACTION_LIMIT:
                if not is_supervisor_approved:
                    return GateDecision(
                        decision="REQUIRE_APPROVAL",
                        reason_code="TIER2_APPROVAL_REQUIRED",
                        reason_detail=f"Amount INR {amount:,.2f} exceeds auto-action limit ₹{settings.AUTO_ACTION_LIMIT:,.2f}. Pausing for supervisor authorization in Human Console.",
                        policy_citations=citations,
                        allowed=False,
                        requires_approval=True,
                        is_denied=False
                    )
                # If supervisor approved, proceed to ALLOW

        # Everything passed
        citations.append("[POL-FPR-001: Rule FPR-2 (failed_payment_reversal.md)]")
        return GateDecision(
            decision="ALLOW",
            reason_code="AUTO_ACTION_PERMITTED",
            reason_detail="All deterministic checks passed: customer verified, state confirmed FAILED, debit confirmed, within limit, no risk flags, zero previous executions.",
            policy_citations=citations,
            allowed=True,
            requires_approval=False,
            is_denied=False
        )

permission_gate = DeterministicPermissionGate()

