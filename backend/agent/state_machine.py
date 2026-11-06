import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import Case, CaseStep, HumanApprovalQueue, IdempotencyRecord
from backend.db.audit import log_audit_event, mask_pii_string, mask_pii_data
from backend.gate.permission_gate import permission_gate, GateDecision
from backend.policies.rag import policy_rag
from backend.tools.executor import ToolExecutor
from .llm import llm_wrapper, LLMProposal
from .guards import OutputGuard
from .brief import build_case_brief, CaseBrief

class CaseExecutionResult:
    def __init__(
        self,
        case_id: Optional[str],
        status: str,
        outcome: Optional[str],
        customer_message: str,
        status_chip: str,
        steps: List[Dict[str, Any]],
        case_brief: Optional[Dict[str, Any]] = None,
        is_faq: bool = False
    ):
        self.case_id = case_id
        self.status = status
        self.outcome = outcome
        self.customer_message = customer_message
        self.status_chip = status_chip
        self.steps = steps
        self.case_brief = case_brief
        self.is_faq = is_faq

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "outcome": self.outcome,
            "customer_message": self.customer_message,
            "status_chip": self.status_chip,
            "steps": self.steps,
            "case_brief": self.case_brief,
            "is_faq": self.is_faq
        }

class SaarthiOrchestrator:
    """
    Explicit State Machine for Payment Dispute Resolution.
    States:
      UNDERSTAND -> INVESTIGATE -> DECIDE -> GATE -> ACT -> VERIFY -> INFORM / ESCALATE -> DONE
    """

    def __init__(self, db: Session):
        self.db = db
        self.executor = ToolExecutor(db)
        self.recorded_steps: List[Dict[str, Any]] = []

    def _record_step(self, case_id: Optional[str], step_name: str, status: str, state_data: Dict[str, Any]):
        step_entry = {
            "step_name": step_name,
            "status": status,
            "state_data": mask_pii_data(state_data),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.recorded_steps.append(step_entry)
        if case_id:
            db_step = CaseStep(
                case_id=case_id,
                step_name=step_name,
                status=status,
                state_data=json.dumps(mask_pii_data(state_data), default=str)
            )
            self.db.add(db_step)
            self.db.commit()

    async def run(
        self,
        complaint_text: str,
        customer_id: str = "CUST-4921",
        customer_auth: Optional[Dict[str, Any]] = None,
        case_id: Optional[str] = None,
        is_supervisor_approval: bool = False
    ) -> CaseExecutionResult:
        if customer_auth is None:
            customer_auth = {
                "authenticated": True,
                "auth_method": "APP_SESSION_TOKEN",
                "customer_id": customer_id
            }

        actions_attempted = []
        results_observed = []
        checks_performed = []
        policies_consulted = []
        case_record = None

        # =========================================================================
        # 1. STATE: UNDERSTAND
        # =========================================================================
        proposal = await llm_wrapper.analyze_complaint(complaint_text, customer_id)
        lang = proposal.language

        self._record_step(
            case_id=case_id,
            step_name="UNDERSTAND",
            status="SUCCESS",
            state_data={
                "intent": proposal.intent,
                "language": lang,
                "extracted_txn_id": proposal.extracted_txn_id,
                "extracted_amount": proposal.extracted_amount,
                "extracted_merchant": proposal.extracted_merchant,
                "reasoning": proposal.reasoning
            }
        )
        checks_performed.append("Customer intent parsed and language identified")

        # Scenario I: General informational FAQ, Greeting, or Out of Scope
        if proposal.is_faq and proposal.faq_response:
            is_safe, safe_faq = OutputGuard.sanitize_and_validate(proposal.faq_response)
            self._record_step(
                case_id=None,
                step_name="DONE",
                status="SUCCESS",
                state_data={"outcome": "FAQ_ANSWERED", "message": safe_faq}
            )
            return CaseExecutionResult(
                case_id=None,
                status="CLOSED",
                outcome="FAQ_ANSWERED",
                customer_message=safe_faq,
                status_chip=None,
                steps=self.recorded_steps,
                is_faq=True
            )

        # Generate or locate Case in database
        if not case_id:
            case_id = f"CASE-{customer_id[-4:]}-{uuid.uuid4().hex[:6].upper()}"

        case_record = self.db.query(Case).filter(Case.id == case_id).first()
        if not case_record:
            case_record = Case(
                id=case_id,
                customer_id=customer_id,
                txn_id=proposal.extracted_txn_id,
                complaint_text=complaint_text,
                customer_language=lang,
                status="INVESTIGATING"
            )
            self.db.add(case_record)
            self.db.commit()

        # =========================================================================
        # 2. STATE: INVESTIGATE
        # =========================================================================
        lookup_args = {
            "txn_id": proposal.extracted_txn_id,
            "customer_id": customer_id,
            "amount": proposal.extracted_amount
        }
        lookup_res = await self.executor.execute("lookup_transaction", lookup_args, case_id)
        checks_performed.append("Authoritative Payments Core transaction lookup")

        if not lookup_res.success or not lookup_res.data:
            # Rule 2: Never infer status on lookup failure
            reason = f"Transaction lookup failed: {lookup_res.error or 'Record not found'}. Cannot infer transaction status."
            brief = build_case_brief(
                case_id=case_id,
                original_issue=complaint_text,
                transaction_info={"customer_id": customer_id, "status": "UNCONFIRMED"},
                actions_attempted=actions_attempted,
                results_observed=results_observed,
                checks_performed=checks_performed,
                policies_consulted=["[POL-ESC-005: Rule ESC-1 (escalation_and_risk.md)]"],
                reason_for_escalation=reason,
                recommended_next_step="Contact customer to verify transaction identifier or billing bank statement."
            )
            self._record_step(case_id, "INVESTIGATE", "FAILED", {"error": lookup_res.error})
            self._record_step(case_id, "ESCALATE", "SUCCESS", {"brief": brief.model_dump()})

            msg = "We were unable to locate this transaction in our payments core. Case has been escalated to an operations specialist to verify your account."
            _, safe_msg = OutputGuard.sanitize_and_validate(msg)
            case_record.status = "ESCALATED"
            case_record.outcome = "LOOKUP_FAILED"
            case_record.case_brief = brief.to_markdown()
            self.db.commit()

            return CaseExecutionResult(
                case_id=case_id,
                status="ESCALATED",
                outcome="LOOKUP_FAILED",
                customer_message=safe_msg,
                status_chip="ESCALATED",
                steps=self.recorded_steps,
                case_brief=brief.model_dump()
            )

        # Handle single vs list data from lookup
        if isinstance(lookup_res.data, list) and lookup_res.data:
            if proposal.extracted_txn_id:
                matched = [t for t in lookup_res.data if t.get("txn_id") == proposal.extracted_txn_id]
                txn_data = matched[0] if matched else lookup_res.data[0]
            elif proposal.extracted_merchant:
                matched = [t for t in lookup_res.data if proposal.extracted_merchant.lower() in t.get("merchant", "").lower()]
                txn_data = matched[0] if matched else lookup_res.data[0]
            else:
                # Prioritize active dispute states (FAILED, PENDING_CONFIRMATION, DUPLICATE_DEBIT) over already REVERSED or SUCCESS
                dispute_txns = [t for t in lookup_res.data if t.get("status") in ("FAILED", "PENDING_CONFIRMATION", "DUPLICATE_DEBIT")]
                txn_data = dispute_txns[0] if dispute_txns else lookup_res.data[0]
        else:
            txn_data = lookup_res.data
        txn_id = txn_data.get("txn_id")
        case_record.txn_id = txn_id
        self.db.commit()

        # Authoritative status check
        status_res = await self.executor.execute("check_transaction_status", {"txn_id": txn_id}, case_id)
        if not status_res.success:
            reason = f"Authoritative switch status check failed: {status_res.error}"
            brief = build_case_brief(
                case_id=case_id,
                original_issue=complaint_text,
                transaction_info=txn_data,
                actions_attempted=actions_attempted,
                results_observed=results_observed,
                checks_performed=checks_performed,
                policies_consulted=["[POL-ESC-005: Rule ESC-1 (escalation_and_risk.md)]"],
                reason_for_escalation=reason,
                recommended_next_step="Check switch connectivity and retry authoritative settlement query."
            )
            case_record.status = "ESCALATED"
            case_record.outcome = "STATUS_CHECK_FAILED"
            case_record.case_brief = brief.to_markdown()
            self.db.commit()

            msg = "Upstream banking switch is currently unreachable. Your case is tracked and escalated for automated retry."
            return CaseExecutionResult(case_id=case_id, status="ESCALATED", outcome="STATUS_CHECK_FAILED", customer_message=msg, status_chip="ESCALATED", steps=self.recorded_steps, case_brief=brief.model_dump())

        confirmed_status = status_res.data.get("status")
        txn_data.update(status_res.data)

        self._record_step(
            case_id=case_id,
            step_name="INVESTIGATE",
            status="SUCCESS",
            state_data={
                "txn_id": txn_id,
                "status": confirmed_status,
                "status_source": txn_data.get("status_source"),
                "debit_confirmed": txn_data.get("debit_confirmed"),
                "credit_confirmed": txn_data.get("credit_confirmed"),
                "risk_flags": txn_data.get("risk_flags"),
                "amount": txn_data.get("amount"),
                "merchant": txn_data.get("merchant")
            }
        )

        # Scenario B: PENDING_CONFIRMATION
        if confirmed_status == "PENDING_CONFIRMATION":
            checks_performed.append("Verified PENDING_CONFIRMATION status with payments clearing switch")
            policies_consulted.extend([
                "[POL-PSH-002: Rule PSH-1 (pending_status_handling.md)]",
                "[POL-PSH-002: Rule PSH-2 (pending_status_handling.md)]",
                "[POL-PSH-002: Rule PSH-3 (pending_status_handling.md)]"
            ])
            brief = build_case_brief(
                case_id=case_id,
                original_issue=complaint_text,
                transaction_info=txn_data,
                actions_attempted=["Core switch status verification"],
                results_observed=["Transaction pending clearing settlement at NPCI/issuing bank"],
                checks_performed=checks_performed,
                policies_consulted=policies_consulted,
                reason_for_escalation="Transaction is UNCONFIRMED (PENDING_CONFIRMATION). Strict policy prohibition against premature reversal or status inference.",
                recommended_next_step="Await bank settlement batch at T+24h. Trigger automated reconciliation listener."
            )
            case_record.status = "AWAITING_STATUS_CHANGE"
            case_record.outcome = "UNCONFIRMED_PENDING"
            case_record.case_brief = brief.to_markdown()
            self.db.commit()

            msg = llm_wrapper.format_customer_message(
                case_id=case_id,
                template_type="UNCONFIRMED_PENDING",
                lang=lang,
                context={"amount": txn_data.get("amount"), "merchant": txn_data.get("merchant")}
            )
            self._record_step(case_id, "ESCALATE", "SUCCESS", {"outcome": "AWAITING_STATUS_CHANGE", "brief": brief.model_dump()})
            self._record_step(case_id, "INFORM", "SUCCESS", {"customer_message": msg, "chip": "AWAITING_STATUS_CHANGE"})
            self._record_step(case_id, "DONE", "SUCCESS", {"final_state": "AWAITING_STATUS_CHANGE"})

            return CaseExecutionResult(
                case_id=case_id,
                status="AWAITING_STATUS_CHANGE",
                outcome="UNCONFIRMED_PENDING",
                customer_message=msg,
                status_chip="AWAITING_STATUS_CHANGE",
                steps=self.recorded_steps,
                case_brief=brief.model_dump()
            )

        # =========================================================================
        # 3. STATE: DECIDE
        # =========================================================================
        policy_res = await self.executor.execute(
            "retrieve_policy",
            {"query": f"{confirmed_status} payment reversal limit risk rules", "top_k": 3},
            case_id
        )
        if policy_res.success and policy_res.data:
            policies_consulted.extend(policy_res.data.get("citations", []))

        permitted_res = await self.executor.execute(
            "get_permitted_actions",
            {
                "status": confirmed_status,
                "debit_confirmed": bool(txn_data.get("debit_confirmed")),
                "credit_confirmed": bool(txn_data.get("credit_confirmed"))
            },
            case_id
        )
        permitted_actions = permitted_res.data.get("permitted_actions", [])

        # Propose reversal if eligible, otherwise escalate
        proposed_action = "initiate_reversal" if "initiate_reversal" in permitted_actions else "escalate_to_human"

        self._record_step(
            case_id=case_id,
            step_name="DECIDE",
            status="SUCCESS",
            state_data={
                "confirmed_status": confirmed_status,
                "permitted_actions": permitted_actions,
                "proposed_action": proposed_action,
                "policies_consulted": policies_consulted
            }
        )

        # =========================================================================
        # 4. STATE: GATE (Deterministic Python Permission Gate)
        # =========================================================================
        idempotency_key = f"REV-{txn_id}"
        gate_decision: GateDecision = permission_gate.evaluate(
            proposed_action=proposed_action,
            txn_data=txn_data,
            customer_auth=customer_auth,
            idempotency_key=idempotency_key,
            db=self.db,
            is_supervisor_approved=is_supervisor_approval
        )
        policies_consulted.extend(gate_decision.policy_citations)

        self._record_step(
            case_id=case_id,
            step_name="GATE",
            status="SUCCESS" if gate_decision.allowed else "HALTED",
            state_data={
                "gate_decision": gate_decision.decision,
                "reason_code": gate_decision.reason_code,
                "reason_detail": gate_decision.reason_detail,
                "policy_citations": gate_decision.policy_citations
            }
        )
        checks_performed.append(f"Deterministic Permission Gate evaluated: {gate_decision.decision} ({gate_decision.reason_code})")

        # Scenario E: REQUIRE_APPROVAL (> ₹5,000 auto limit)
        if gate_decision.requires_approval:
            brief = build_case_brief(
                case_id=case_id,
                original_issue=complaint_text,
                transaction_info=txn_data,
                actions_attempted=actions_attempted,
                results_observed=results_observed,
                checks_performed=checks_performed,
                policies_consulted=policies_consulted,
                reason_for_escalation=gate_decision.reason_detail,
                recommended_next_step="Approve autonomous reversal execution via Human Console if merchant dispute validation passes."
            )
            # Add to supervisor queue
            approval_entry = HumanApprovalQueue(
                id=f"APPR-{case_id}",
                case_id=case_id,
                txn_id=txn_id,
                amount=float(txn_data.get("amount", 0.0)),
                action_proposed="initiate_reversal",
                gate_reason=gate_decision.reason_detail,
                case_brief=brief.to_markdown(),
                status="PENDING"
            )
            self.db.add(approval_entry)
            case_record.status = "PENDING_APPROVAL"
            case_record.outcome = "REQUIRE_APPROVAL"
            case_record.case_brief = brief.to_markdown()
            self.db.commit()

            msg = llm_wrapper.format_customer_message(
                case_id=case_id,
                template_type="REQUIRE_APPROVAL",
                lang=lang,
                context={"amount": txn_data.get("amount"), "merchant": txn_data.get("merchant")}
            )
            self._record_step(case_id, "ESCALATE", "PAUSED", {"approval_id": approval_entry.id, "brief": brief.model_dump()})
            self._record_step(case_id, "INFORM", "SUCCESS", {"customer_message": msg, "chip": "ESCALATED"})

            return CaseExecutionResult(
                case_id=case_id,
                status="PENDING_APPROVAL",
                outcome="REQUIRE_APPROVAL",
                customer_message=msg,
                status_chip="ESCALATED",
                steps=self.recorded_steps,
                case_brief=brief.model_dump()
            )

        # DENY handling (e.g. Scenario D: Risk Flag, Scenario G: Idempotency violation)
        if gate_decision.is_denied:
            if gate_decision.reason_code == "IDEMPOTENCY_VIOLATION":
                msg = llm_wrapper.format_customer_message(
                    case_id=case_id,
                    template_type="IDEMPOTENCY_BLOCKED",
                    lang=lang,
                    context={"rrn": f"REV-{txn_id}"}
                )
                case_record.status = "RESOLVED"
                case_record.outcome = "IDEMPOTENT_ALREADY_RESOLVED"
                self.db.commit()
                self._record_step(case_id, "INFORM", "SUCCESS", {"customer_message": msg, "chip": "RESOLVED_VERIFIED"})
                self._record_step(case_id, "DONE", "SUCCESS", {"final_state": "RESOLVED"})
                return CaseExecutionResult(
                    case_id=case_id,
                    status="RESOLVED",
                    outcome="IDEMPOTENT_ALREADY_RESOLVED",
                    customer_message=msg,
                    status_chip="RESOLVED_VERIFIED",
                    steps=self.recorded_steps
                )

            # Security / Risk / Ineligible denial
            brief = build_case_brief(
                case_id=case_id,
                original_issue=complaint_text,
                transaction_info=txn_data,
                actions_attempted=actions_attempted,
                results_observed=results_observed,
                checks_performed=checks_performed,
                policies_consulted=policies_consulted,
                reason_for_escalation=gate_decision.reason_detail,
                recommended_next_step="Security operations review required. Inspect account device velocity and merchant network alerts."
            )
            case_record.status = "ESCALATED"
            case_record.outcome = f"GATE_DENIED_{gate_decision.reason_code}"
            case_record.case_brief = brief.to_markdown()
            self.db.commit()

            msg = llm_wrapper.format_customer_message(
                case_id=case_id,
                template_type="ESCALATED_RISK",
                lang=lang,
                context={"amount": txn_data.get("amount")}
            )
            self._record_step(case_id, "ESCALATE", "SUCCESS", {"brief": brief.model_dump()})
            self._record_step(case_id, "INFORM", "SUCCESS", {"customer_message": msg, "chip": "ESCALATED"})
            self._record_step(case_id, "DONE", "SUCCESS", {"final_state": "ESCALATED"})

            return CaseExecutionResult(
                case_id=case_id,
                status="ESCALATED",
                outcome=f"GATE_DENIED_{gate_decision.reason_code}",
                customer_message=msg,
                status_chip="ESCALATED",
                steps=self.recorded_steps,
                case_brief=brief.model_dump()
            )

        # =========================================================================
        # 5. STATE: ACT
        # =========================================================================
        actions_attempted.append(f"initiate_reversal(txn_id={txn_id}, idempotency_key={idempotency_key})")
        rev_res = await self.executor.execute(
            "initiate_reversal",
            {
                "txn_id": txn_id,
                "reason": "Payment confirmed FAILED with customer debit confirmed. Reversal policy FPR-1 satisfied.",
                "idempotency_key": idempotency_key
            },
            case_id
        )

        if not rev_res.success:
            results_observed.append(f"Reversal API failed: {rev_res.error}")
            brief = build_case_brief(
                case_id=case_id,
                original_issue=complaint_text,
                transaction_info=txn_data,
                actions_attempted=actions_attempted,
                results_observed=results_observed,
                checks_performed=checks_performed,
                policies_consulted=policies_consulted,
                reason_for_escalation=f"Payments core reversal invocation failed: {rev_res.error}",
                recommended_next_step="Manually inspect acquirer gateway reversal queue."
            )
            case_record.status = "ESCALATED"
            case_record.outcome = "REVERSAL_EXECUTION_FAILED"
            case_record.case_brief = brief.to_markdown()
            self.db.commit()

            msg = "Reversal order could not be completed by the core banking switch. Escalated to payments operations."
            return CaseExecutionResult(case_id=case_id, status="ESCALATED", outcome="REVERSAL_EXECUTION_FAILED", customer_message=msg, status_chip="ESCALATED", steps=self.recorded_steps, case_brief=brief.model_dump())

        results_observed.append("Reversal order transmitted to core clearing switch")
        reversal_ref = rev_res.data.get("reversal_ref", "REV-CONFIRMED")
        self._record_step(
            case_id=case_id,
            step_name="ACT",
            status="SUCCESS",
            state_data={"reversal_res": rev_res.data}
        )

        # =========================================================================
        # 6. STATE: VERIFY (Zero-Assumption Post-Action State Re-Check)
        # =========================================================================
        # Non-negotiable Rule 3: Reversal is NOT assumed to have worked.
        verify_status_res = await self.executor.execute("check_transaction_status", {"txn_id": txn_id}, case_id)
        checks_performed.append("Authoritative post-action state re-check")

        rechecked_status = verify_status_res.data.get("status") if verify_status_res.success else "UNKNOWN"
        recheck_passed = rechecked_status in ("REVERSED", "REVERSAL_PENDING")

        self._record_step(
            case_id=case_id,
            step_name="VERIFY",
            status="SUCCESS" if recheck_passed else "FAILED",
            state_data={
                "expected_status": ["REVERSED", "REVERSAL_PENDING"],
                "rechecked_status": rechecked_status,
                "verified": recheck_passed,
                "reversal_ref": reversal_ref
            }
        )

        # Scenario F: Verification mismatch failure
        if not recheck_passed:
            results_observed.append(f"Post-action state re-check showed status '{rechecked_status}' instead of REVERSED.")
            brief = build_case_brief(
                case_id=case_id,
                original_issue=complaint_text,
                transaction_info=txn_data,
                actions_attempted=actions_attempted,
                results_observed=results_observed,
                checks_performed=checks_performed,
                policies_consulted=policies_consulted,
                reason_for_escalation="Verification Failure: Reversal API reported success, but authoritative post-action state re-check did NOT transition to REVERSED.",
                recommended_next_step="Inspect upstream settlement ledger to resolve transaction state mismatch."
            )
            case_record.status = "ESCALATED"
            case_record.outcome = "VERIFICATION_MISMATCH"
            case_record.case_brief = brief.to_markdown()
            self.db.commit()

            msg = llm_wrapper.format_customer_message(
                case_id=case_id,
                template_type="VERIFICATION_FAILED",
                lang=lang,
                context={"amount": txn_data.get("amount")}
            )
            self._record_step(case_id, "ESCALATE", "SUCCESS", {"brief": brief.model_dump()})
            self._record_step(case_id, "INFORM", "SUCCESS", {"customer_message": msg, "chip": "ESCALATED"})
            self._record_step(case_id, "DONE", "SUCCESS", {"final_state": "ESCALATED"})

            return CaseExecutionResult(
                case_id=case_id,
                status="ESCALATED",
                outcome="VERIFICATION_MISMATCH",
                customer_message=msg,
                status_chip="ESCALATED",
                steps=self.recorded_steps,
                case_brief=brief.model_dump()
            )

        # =========================================================================
        # 7. STATE: INFORM
        # =========================================================================
        msg = llm_wrapper.format_customer_message(
            case_id=case_id,
            template_type="RESOLVED_VERIFIED",
            lang=lang,
            context={
                "amount": txn_data.get("amount"),
                "merchant": txn_data.get("merchant"),
                "rrn": reversal_ref,
                "tat": "24 to 48 business hours"
            }
        )
        case_record.status = "RESOLVED"
        case_record.outcome = "VERIFIED_REVERSAL"
        case_record.resolved_at = datetime.utcnow()
        case_record.resolution_notes = f"Verified reversal confirmed. Ref: {reversal_ref}"
        self.db.commit()

        self._record_step(
            case_id=case_id,
            step_name="INFORM",
            status="SUCCESS",
            state_data={"customer_message": msg, "status_chip": "RESOLVED_VERIFIED", "rrn": reversal_ref}
        )

        # =========================================================================
        # 8. STATE: DONE
        # =========================================================================
        self._record_step(
            case_id=case_id,
            step_name="DONE",
            status="SUCCESS",
            state_data={"final_state": "RESOLVED", "outcome": "VERIFIED_REVERSAL"}
        )

        return CaseExecutionResult(
            case_id=case_id,
            status="RESOLVED",
            outcome="VERIFIED_REVERSAL",
            customer_message=msg,
            status_chip="RESOLVED_VERIFIED",
            steps=self.recorded_steps
        )

