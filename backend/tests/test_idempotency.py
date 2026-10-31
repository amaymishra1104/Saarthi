import pytest
from backend.gate.permission_gate import permission_gate
from backend.db.models import IdempotencyRecord

def test_idempotency_blocks_duplicate_reversal(db_session):
    txn_id = "TXN-IDEMP-1"
    txn_data = {
        "txn_id": txn_id,
        "customer_id": "CUST-4921",
        "amount": 2000.0,
        "status": "FAILED",
        "debit_confirmed": True,
        "credit_confirmed": False,
        "risk_flags": [],
        "reversal_eligible": True
    }
    auth = {"authenticated": True, "customer_id": "CUST-4921"}
    key = f"REV-{txn_id}"

    # First evaluation: ALLOWED
    d1 = permission_gate.evaluate(
        proposed_action="initiate_reversal",
        txn_data=txn_data,
        customer_auth=auth,
        idempotency_key=key,
        db=db_session
    )
    assert d1.allowed is True

    # Record first execution in database
    rec = IdempotencyRecord(
        idempotency_key=key,
        action_type="initiate_reversal",
        txn_id=txn_id,
        case_id="CASE-001",
        status="EXECUTED"
    )
    db_session.add(rec)
    db_session.commit()

    # Second evaluation with same key: DENIED
    d2 = permission_gate.evaluate(
        proposed_action="initiate_reversal",
        txn_data=txn_data,
        customer_auth=auth,
        idempotency_key=key,
        db=db_session
    )
    assert d2.allowed is False
    assert d2.decision == "DENY"
    assert d2.reason_code == "IDEMPOTENCY_VIOLATION"

def test_idempotency_blocks_same_action_different_key_on_same_txn(db_session):
    txn_id = "TXN-IDEMP-2"
    rec = IdempotencyRecord(
        idempotency_key="REV-TXN-IDEMP-2-KEYA",
        action_type="initiate_reversal",
        txn_id=txn_id,
        case_id="CASE-002",
        status="EXECUTED"
    )
    db_session.add(rec)
    db_session.commit()

    txn_data = {
        "txn_id": txn_id,
        "customer_id": "CUST-4921",
        "amount": 1000.0,
        "status": "FAILED",
        "debit_confirmed": True,
        "credit_confirmed": False,
        "risk_flags": [],
        "reversal_eligible": True
    }
    auth = {"authenticated": True, "customer_id": "CUST-4921"}
    d = permission_gate.evaluate(
        proposed_action="initiate_reversal",
        txn_data=txn_data,
        customer_auth=auth,
        idempotency_key="REV-TXN-IDEMP-2-KEYB",
        db=db_session
    )
    assert d.allowed is False
    assert d.reason_code == "IDEMPOTENCY_VIOLATION"

