import pytest
from backend.agent.state_machine import SaarthiOrchestrator
from backend.mock_payments.service import mock_payments_service

@pytest.mark.asyncio
async def test_failure_matrix_1_lookup_fails_escalate_never_infer(db_session):
    """1. Lookup fails -> escalate, never infer a status"""
    mock_payments_service.set_chaos(lookup_fail=True)
    orchestrator = SaarthiOrchestrator(db_session)

    res = await orchestrator.run("My transaction TXN-1001 of ₹2,000 failed. Refund me.", customer_id="CUST-4921")
    assert res.status == "ESCALATED"
    assert res.outcome == "LOOKUP_FAILED"
    assert "unable to locate this transaction" in res.customer_message or "escalated" in res.customer_message
    assert res.case_brief is not None
    assert "Cannot infer transaction status" in res.case_brief["reason_for_escalation"]

@pytest.mark.asyncio
async def test_failure_matrix_2_api_timeout_retries_and_escalates(db_session):
    """2. API timeout -> retry within limits, re-check state first, escalate on exhaustion"""
    mock_payments_service.set_chaos(api_timeout=True)
    orchestrator = SaarthiOrchestrator(db_session)

    res = await orchestrator.run("Status check on TXN-1001", customer_id="CUST-4921")
    assert res.status == "ESCALATED"
    assert res.case_brief is not None
    assert "Gateway Timeout" in res.case_brief["reason_for_escalation"]

@pytest.mark.asyncio
async def test_failure_matrix_3_ambiguous_pending_status_never_infer(db_session):
    """3. Status ambiguous / pending -> treat as unconfirmed, escalate, promise notification"""
    mock_payments_service.set_chaos(ambiguous_status=True)
    orchestrator = SaarthiOrchestrator(db_session)

    res = await orchestrator.run("Did my transaction TXN-1001 go through?", customer_id="CUST-4921")
    assert res.status == "AWAITING_STATUS_CHANGE"
    assert res.status_chip == "AWAITING_STATUS_CHANGE"
    assert "I can't call it failed or successful yet" in res.customer_message
    assert res.case_brief is not None
    assert "PENDING_CONFIRMATION" in res.case_brief["reason_for_escalation"]

@pytest.mark.asyncio
async def test_failure_matrix_4_duplicate_attempt_idempotency_blocks(db_session):
    """4. Duplicate attempt -> idempotency key blocks the second run"""
    orchestrator = SaarthiOrchestrator(db_session)

    # First run succeeds
    res1 = await orchestrator.run("₹2,000 debited on Zomato TXN-1001 failed.", customer_id="CUST-4921")
    assert res1.status == "RESOLVED"
    assert res1.outcome == "VERIFIED_REVERSAL"

    # Second identical run hits idempotency guard
    res2 = await orchestrator.run("₹2,000 debited on Zomato TXN-1001 failed.", customer_id="CUST-4921")
    assert res2.outcome == "IDEMPOTENT_ALREADY_RESOLVED"
    assert "already been initiated" in res2.customer_message

@pytest.mark.asyncio
async def test_failure_matrix_5_verification_fails_unresolved_escalated(db_session):
    """5. Verification fails -> report as unresolved, escalate"""
    # TXN-1006 triggers verification mismatch in mock payments service
    orchestrator = SaarthiOrchestrator(db_session)

    res = await orchestrator.run("My payment TXN-1006 of ₹1,800 failed on Uber. Please reverse.", customer_id="CUST-6120")
    assert res.status == "ESCALATED"
    assert res.outcome == "VERIFICATION_MISMATCH"
    assert res.status_chip == "ESCALATED"
    assert "verification check did not confirm settlement" in res.customer_message
    assert res.case_brief is not None
    assert "Verification Failure" in res.case_brief["reason_for_escalation"]

@pytest.mark.asyncio
async def test_failure_matrix_6_approval_required_pauses_for_human(db_session):
    """6. Approval required -> pause and queue for a human"""
    orchestrator = SaarthiOrchestrator(db_session)

    # TXN-1005 is ₹12,000 (above ₹5,000 auto limit)
    res = await orchestrator.run("My payment of ₹12,000 for Croma TXN-1005 failed.", customer_id="CUST-5541")
    assert res.status == "PENDING_APPROVAL"
    assert res.outcome == "REQUIRE_APPROVAL"
    assert "supervisor" in res.customer_message.lower()
    assert res.case_brief is not None
    assert "exceeds auto-action limit" in res.case_brief["reason_for_escalation"].lower()

