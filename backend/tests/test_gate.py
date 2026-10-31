import pytest
from backend.gate.permission_gate import permission_gate
from backend.db.models import IdempotencyRecord

def test_gate_allows_valid_reversal(db_session):
    txn_data = {
        "txn_id": "TXN-TEST-1",
        "customer_id": "CUST-4921",
        "amount": 2000.0,
        "status": "FAILED",
        "debit_confirmed": True,
        "credit_confirmed": False,
        "risk_flags": [],
        "reversal_eligible": True
    }
    auth = {"authenticated": True, "customer_id": "CUST-4921"}
    decision = permission_gate.evaluate(
        proposed_action="initiate_reversal",
        txn_data=txn_data,
        customer_auth=auth,
        idempotency_key="REV-TXN-TEST-1",
        db=db_session
    )
    assert decision.allowed is True
    assert decision.decision == "ALLOW"
    assert decision.reason_code == "AUTO_ACTION_PERMITTED"
    assert len(decision.policy_citations) > 0

def test_gate_requires_approval_above_limit(db_session):
    txn_data = {
        "txn_id": "TXN-TEST-2",
        "customer_id": "CUST-4921",
        "amount": 12000.0,  # Exceeds 5k limit
        "status": "FAILED",
        "debit_confirmed": True,
        "credit_confirmed": False,
        "risk_flags": [],
        "reversal_eligible": True
    }
    auth = {"authenticated": True, "customer_id": "CUST-4921"}
    decision = permission_gate.evaluate(
        proposed_action="initiate_reversal",
        txn_data=txn_data,
        customer_auth=auth,
        idempotency_key="REV-TXN-TEST-2",
        db=db_session
    )
    assert decision.allowed is False
    assert decision.requires_approval is True
    assert decision.decision == "REQUIRE_APPROVAL"
    assert decision.reason_code == "TIER2_APPROVAL_REQUIRED"

def test_gate_allows_when_supervisor_approved(db_session):
    txn_data = {
        "txn_id": "TXN-TEST-2",
        "customer_id": "CUST-4921",
        "amount": 12000.0,
        "status": "FAILED",
        "debit_confirmed": True,
        "credit_confirmed": False,
        "risk_flags": [],
        "reversal_eligible": True
    }
    auth = {"authenticated": True, "customer_id": "CUST-4921"}
    decision = permission_gate.evaluate(
        proposed_action="initiate_reversal",
        txn_data=txn_data,
        customer_auth=auth,
        idempotency_key="REV-TXN-TEST-2",
        db=db_session,
        is_supervisor_approved=True
    )
    assert decision.allowed is True
    assert decision.decision == "ALLOW"

def test_gate_denies_on_risk_flag(db_session):
    txn_data = {
        "txn_id": "TXN-TEST-3",
        "customer_id": "CUST-4921",
        "amount": 1500.0,
        "status": "FLAGGED_RISK",
        "debit_confirmed": True,
        "credit_confirmed": False,
        "risk_flags": ["FRAUD_SUSPECTED"],
        "reversal_eligible": False
    }
    auth = {"authenticated": True, "customer_id": "CUST-4921"}
    decision = permission_gate.evaluate(
        proposed_action="initiate_reversal",
        txn_data=txn_data,
        customer_auth=auth,
        idempotency_key="REV-TXN-TEST-3",
        db=db_session
    )
    assert decision.allowed is False
    assert decision.decision == "DENY"
    assert decision.reason_code == "RISK_FLAG_DETECTED"

def test_gate_denies_pending_confirmation(db_session):
    txn_data = {
        "txn_id": "TXN-TEST-4",
        "customer_id": "CUST-4921",
        "amount": 2000.0,
        "status": "PENDING_CONFIRMATION",
        "debit_confirmed": True,
        "credit_confirmed": False,
        "risk_flags": [],
        "reversal_eligible": False
    }
    auth = {"authenticated": True, "customer_id": "CUST-4921"}
    decision = permission_gate.evaluate(
        proposed_action="initiate_reversal",
        txn_data=txn_data,
        customer_auth=auth,
        idempotency_key="REV-TXN-TEST-4",
        db=db_session
    )
    assert decision.allowed is False
    assert decision.decision == "DENY"
    assert decision.reason_code == "UNCONFIRMED_PENDING_STATUS"

