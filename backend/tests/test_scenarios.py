import pytest
from backend.agent.state_machine import SaarthiOrchestrator
from backend.db.models import HumanApprovalQueue

@pytest.mark.asyncio
async def test_scenario_a_failed_payment_verified_resolution(db_session):
    """Scenario A: ₹2,000 debited, status FAILED, reversal permitted -> Resolved (verified)."""
    orchestrator = SaarthiOrchestrator(db_session)
    res = await orchestrator.run(
        "₹2,000 debited for my Zomato order TXN-1001, but the app says payment failed. Please refund my money.",
        customer_id="CUST-4921"
    )
    assert res.status == "RESOLVED"
    assert res.outcome == "VERIFIED_REVERSAL"
    assert res.status_chip == "RESOLVED_VERIFIED"
    assert "successfully processed and verified" in res.customer_message
    # Check steps
    step_names = [s["step_name"] for s in res.steps]
    assert "UNDERSTAND" in step_names
    assert "INVESTIGATE" in step_names
    assert "DECIDE" in step_names
    assert "GATE" in step_names
    assert "ACT" in step_names
    assert "VERIFY" in step_names
    assert "INFORM" in step_names

@pytest.mark.asyncio
async def test_scenario_b_pending_confirmation_unconfirmed(db_session):
    """Scenario B: ₹2,000 debited, status PENDING_CONFIRMATION -> refuses to call failed/successful, opens tracked case, escalates with brief, tells customer it will message when status changes."""
    orchestrator = SaarthiOrchestrator(db_session)
    res = await orchestrator.run(
        "I paid ₹2,000 on Swiggy TXN-1002, money left my bank account but Swiggy says waiting for bank confirmation.",
        customer_id="CUST-8832"
    )
    assert res.status == "AWAITING_STATUS_CHANGE"
    assert res.outcome == "UNCONFIRMED_PENDING"
    assert res.status_chip == "AWAITING_STATUS_CHANGE"
    # Headline phrase check
    assert "I can't call it failed or successful yet" in res.customer_message
    assert res.case_brief is not None
    assert "bank settlement batch" in res.case_brief["recommended_next_step"].lower()

@pytest.mark.asyncio
async def test_scenario_c_duplicate_debit(db_session):
    """Scenario C: Duplicate debit -> policy lookup, gate check, action or escalation per policy."""
    orchestrator = SaarthiOrchestrator(db_session)
    res = await orchestrator.run(
        "I was charged ₹650 twice for the same Amazon order TXN-1003B! Reverse the extra debit.",
        customer_id="CUST-3319"
    )
    assert res.status == "RESOLVED"
    assert res.outcome == "VERIFIED_REVERSAL"
    assert res.status_chip == "RESOLVED_VERIFIED"

@pytest.mark.asyncio
async def test_scenario_d_risk_flagged_transaction(db_session):
    """Scenario D: Risk-flagged transaction -> no automation, immediate escalation."""
    orchestrator = SaarthiOrchestrator(db_session)
    res = await orchestrator.run(
        "Why was my payment TXN-1004 of ₹3,500 on CryptoPay declined? Refund immediately.",
        customer_id="CUST-9011"
    )
    assert res.status == "ESCALATED"
    assert "GATE_DENIED_RISK_FLAG_DETECTED" in res.outcome
    assert res.status_chip == "ESCALATED"
    assert res.case_brief is not None
    assert "Security operations review required" in res.case_brief["recommended_next_step"]

@pytest.mark.asyncio
async def test_scenario_e_above_auto_limit_approval_flow(db_session):
    """Scenario E: Amount above auto-limit -> REQUIRE_APPROVAL, human approves in console, then Saarthi executes and verifies."""
    orchestrator = SaarthiOrchestrator(db_session)

    # 1. Customer initiates complaint
    res1 = await orchestrator.run(
        "Payment of ₹12,000 for my Croma purchase TXN-1005 failed. Money got cut from my account.",
        customer_id="CUST-5541"
    )
    assert res1.status == "PENDING_APPROVAL"
    assert res1.outcome == "REQUIRE_APPROVAL"
    case_id = res1.case_id

    # Verify placed in approval queue
    approval = db_session.query(HumanApprovalQueue).filter(HumanApprovalQueue.case_id == case_id).first()
    assert approval is not None
    assert approval.status == "PENDING"
    assert approval.amount == 12000.0

    # 2. Supervisor approves in Console
    approval.status = "APPROVED"
    db_session.commit()

    # Saarthi executes and verifies with supervisor authorization
    res2 = await orchestrator.run(
        "Payment of ₹12,000 for my Croma purchase TXN-1005 failed. Money got cut from my account.",
        customer_id="CUST-5541",
        case_id=case_id,
        is_supervisor_approval=True
    )
    assert res2.status == "RESOLVED"
    assert res2.outcome == "VERIFIED_REVERSAL"
    assert res2.status_chip == "RESOLVED_VERIFIED"

@pytest.mark.asyncio
async def test_scenario_f_verification_mismatch(db_session):
    """Scenario F: Reversal API returns success but state re-check does not change -> reported unresolved and escalated."""
    orchestrator = SaarthiOrchestrator(db_session)
    res = await orchestrator.run(
        "My Uber ride TXN-1006 for ₹1,800 failed at payment gateway. Please reverse.",
        customer_id="CUST-6120"
    )
    assert res.status == "ESCALATED"
    assert res.outcome == "VERIFICATION_MISMATCH"
    assert res.status_chip == "ESCALATED"
    assert "verification check did not confirm settlement" in res.customer_message

@pytest.mark.asyncio
async def test_scenario_g_repeat_complaint_idempotency(db_session):
    """Scenario G: Customer sends the same complaint twice -> idempotency blocks a double reversal."""
    orchestrator = SaarthiOrchestrator(db_session)
    # 1st run
    res1 = await orchestrator.run(
        "₹2,000 cut on Flipkart TXN-1007 but payment failed.",
        customer_id="CUST-7744"
    )
    assert res1.status == "RESOLVED"

    # 2nd run
    res2 = await orchestrator.run(
        "₹2,000 cut on Flipkart TXN-1007 but payment failed.",
        customer_id="CUST-7744"
    )
    assert res2.outcome == "IDEMPOTENT_ALREADY_RESOLVED"
    assert "already been initiated" in res2.customer_message

@pytest.mark.asyncio
async def test_scenario_h_hinglish_language_support(db_session):
    """Scenario H: Customer message in Hinglish or Hindi -> correct intent and reply in same language."""
    orchestrator = SaarthiOrchestrator(db_session)
    res = await orchestrator.run(
        "Mera 1500 cut gaya Blinkit TXN-1008 par merchant bola payment fail ho gaya. Paise wapas chahiye.",
        customer_id="CUST-1190"
    )
    assert res.status == "RESOLVED"
    assert res.outcome == "VERIFIED_REVERSAL"
    # Reply must be in Hinglish
    assert any(w in res.customer_message.lower() for w in ["aapka", "reversal", "credit", "paise", "safaltapoorvak"])

@pytest.mark.asyncio
async def test_scenario_i_faq_no_case_created(db_session):
    """Scenario I: General FAQ -> answered briefly, no case created."""
    orchestrator = SaarthiOrchestrator(db_session)
    res = await orchestrator.run(
        "What does a debit mean?",
        customer_id="CUST-4921"
    )
    assert res.is_faq is True
    assert res.case_id is None
    assert "A debit means funds have been deducted" in res.customer_message
