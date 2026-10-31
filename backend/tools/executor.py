import asyncio
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from backend.mock_payments.service import mock_payments_service
from backend.policies.rag import policy_rag
from backend.db.models import Case, IdempotencyRecord, HumanApprovalQueue
from backend.db.audit import log_audit_event, mask_pii_data
from .definitions import (
    LookupTransactionInput,
    CheckTransactionStatusInput,
    RetrievePolicyInput,
    GetPermittedActionsInput,
    InitiateReversalInput,
    CreateCaseInput,
    UpdateCaseInput,
    EscalateToHumanInput,
    SendCustomerUpdateInput
)

class ToolExecutionResult:
    def __init__(self, success: bool, data: Any, error: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }

class ToolExecutor:
    def __init__(self, db: Session):
        self.db = db

    async def execute(self, tool_name: str, arguments: Dict[str, Any], case_id: Optional[str] = None) -> ToolExecutionResult:
        try:
            if tool_name == "lookup_transaction":
                return await self._lookup_transaction(LookupTransactionInput(**arguments), case_id)
            elif tool_name == "check_transaction_status":
                return await self._check_transaction_status(CheckTransactionStatusInput(**arguments), case_id)
            elif tool_name == "retrieve_policy":
                return await self._retrieve_policy(RetrievePolicyInput(**arguments), case_id)
            elif tool_name == "get_permitted_actions":
                return await self._get_permitted_actions(GetPermittedActionsInput(**arguments), case_id)
            elif tool_name == "initiate_reversal":
                return await self._initiate_reversal(InitiateReversalInput(**arguments), case_id)
            elif tool_name == "create_case":
                return await self._create_case(CreateCaseInput(**arguments), case_id)
            elif tool_name == "update_case":
                return await self._update_case(UpdateCaseInput(**arguments), case_id)
            elif tool_name == "escalate_to_human":
                return await self._escalate_to_human(EscalateToHumanInput(**arguments), case_id)
            elif tool_name == "send_customer_update":
                return await self._send_customer_update(SendCustomerUpdateInput(**arguments), case_id)
            else:
                return ToolExecutionResult(
                    success=False,
                    data=None,
                    error=f"Unrecognized tool '{tool_name}'. Only the 9 approved tools are permitted."
                )
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                data=None,
                error=f"Tool '{tool_name}' failed with error: {str(e)}"
            )

    async def _lookup_transaction(self, inp: LookupTransactionInput, case_id: Optional[str]) -> ToolExecutionResult:
        try:
            if inp.txn_id:
                txn = await mock_payments_service.get_transaction(inp.txn_id)
                data = txn.model_dump()
            else:
                txns = await mock_payments_service.search_transactions(
                    customer_id=inp.customer_id,
                    amount=inp.amount,
                    date=inp.date
                )
                data = [t.model_dump() for t in txns]

            log_audit_event(
                self.db,
                actor="SAARTHI_AGENT",
                action="LOOKUP_TRANSACTION",
                case_id=case_id,
                txn_id=inp.txn_id or (data[0]["txn_id"] if isinstance(data, list) and data else None),
                input_payload=inp.model_dump(),
                output_payload=data
            )
            return ToolExecutionResult(success=True, data=data)
        except HTTPException as he:
            log_audit_event(
                self.db,
                actor="SAARTHI_AGENT",
                action="LOOKUP_TRANSACTION_FAILED",
                case_id=case_id,
                input_payload=inp.model_dump(),
                decision_reason=f"HTTP {he.status_code}: {he.detail}"
            )
            return ToolExecutionResult(success=False, data=None, error=f"Lookup failed: {he.detail}")

    async def _check_transaction_status(self, inp: CheckTransactionStatusInput, case_id: Optional[str]) -> ToolExecutionResult:
        # Bounded retries (max 2 retries on timeout, re-checking state each time)
        max_attempts = 2
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                res = await mock_payments_service.check_transaction_status(inp.txn_id)
                log_audit_event(
                    self.db,
                    actor="PAYMENTS_CORE",
                    action="STATUS_CHECK",
                    case_id=case_id,
                    txn_id=inp.txn_id,
                    input_payload=inp.model_dump(),
                    output_payload=res
                )
                return ToolExecutionResult(success=True, data=res)
            except HTTPException as he:
                last_error = f"HTTP {he.status_code}: {he.detail}"
                if attempt < max_attempts and he.status_code == 504:
                    await asyncio.sleep(0.1)
                    continue
                break

        log_audit_event(
            self.db,
            actor="PAYMENTS_CORE",
            action="STATUS_CHECK_FAILED",
            case_id=case_id,
            txn_id=inp.txn_id,
            input_payload=inp.model_dump(),
            decision_reason=last_error
        )
        return ToolExecutionResult(success=False, data=None, error=f"Status check failed: {last_error}")

    async def _retrieve_policy(self, inp: RetrievePolicyInput, case_id: Optional[str]) -> ToolExecutionResult:
        chunks = policy_rag.retrieve(inp.query, top_k=inp.top_k)
        citations = [c["citation"] for c in chunks]
        log_audit_event(
            self.db,
            actor="POLICY_RAG",
            action="RETRIEVE_POLICY",
            case_id=case_id,
            input_payload=inp.model_dump(),
            output_payload={"chunks_count": len(chunks), "citations": citations},
            policy_citations=citations
        )
        return ToolExecutionResult(success=True, data={"chunks": chunks, "citations": citations})

    async def _get_permitted_actions(self, inp: GetPermittedActionsInput, case_id: Optional[str]) -> ToolExecutionResult:
        permitted = []
        status = inp.status.upper()
        if status in ("FAILED", "DUPLICATE_DEBIT"):
            if inp.debit_confirmed and not inp.credit_confirmed:
                permitted.append("initiate_reversal")
        elif status == "PENDING_CONFIRMATION":
            permitted.append("escalate_to_human")
            permitted.append("send_customer_update")
        elif status == "FLAGGED_RISK":
            permitted.append("escalate_to_human")

        permitted.append("escalate_to_human")
        permitted.append("send_customer_update")

        return ToolExecutionResult(success=True, data={"permitted_actions": permitted, "status": status})

    async def _initiate_reversal(self, inp: InitiateReversalInput, case_id: Optional[str]) -> ToolExecutionResult:
        try:
            res = await mock_payments_service.initiate_reversal(
                txn_id=inp.txn_id,
                idempotency_key=inp.idempotency_key,
                reason=inp.reason
            )
            # Record idempotency key in DB
            rec = IdempotencyRecord(
                idempotency_key=inp.idempotency_key,
                action_type="initiate_reversal",
                txn_id=inp.txn_id,
                case_id=case_id or "UNKNOWN",
                status="EXECUTED",
                response_payload=json.dumps(res.model_dump(), default=str)
            )
            self.db.add(rec)
            self.db.commit()

            log_audit_event(
                self.db,
                actor="SAARTHI_AGENT",
                action="INITIATE_REVERSAL_EXECUTED",
                case_id=case_id,
                txn_id=inp.txn_id,
                input_payload=inp.model_dump(),
                output_payload=res.model_dump(),
                decision_reason=inp.reason
            )
            return ToolExecutionResult(success=True, data=res.model_dump())
        except HTTPException as he:
            log_audit_event(
                self.db,
                actor="SAARTHI_AGENT",
                action="INITIATE_REVERSAL_REJECTED",
                case_id=case_id,
                txn_id=inp.txn_id,
                input_payload=inp.model_dump(),
                decision_reason=f"HTTP {he.status_code}: {he.detail}"
            )
            return ToolExecutionResult(success=False, data=None, error=f"Reversal failed: {he.detail}")

    async def _create_case(self, inp: CreateCaseInput, case_id: Optional[str]) -> ToolExecutionResult:
        cid = case_id or f"CASE-{inp.customer_id[-4:] if len(inp.customer_id)>=4 else '0000'}-{int(asyncio.get_event_loop().time()*1000)%10000:04d}"
        case = Case(
            id=cid,
            customer_id=inp.customer_id,
            txn_id=inp.txn_id,
            complaint_text=inp.complaint_text,
            status="OPEN"
        )
        self.db.add(case)
        self.db.commit()

        log_audit_event(
            self.db,
            actor="SAARTHI_AGENT",
            action="CREATE_CASE",
            case_id=cid,
            txn_id=inp.txn_id,
            input_payload=inp.model_dump(),
            output_payload={"case_id": cid, "status": "OPEN"}
        )
        return ToolExecutionResult(success=True, data={"case_id": cid, "status": "OPEN"})

    async def _update_case(self, inp: UpdateCaseInput, case_id: Optional[str]) -> ToolExecutionResult:
        case = self.db.query(Case).filter(Case.id == inp.case_id).first()
        if not case:
            return ToolExecutionResult(success=False, data=None, error=f"Case {inp.case_id} not found")

        case.status = inp.status
        if inp.outcome:
            case.outcome = inp.outcome
        if inp.resolution_notes:
            case.resolution_notes = inp.resolution_notes

        self.db.commit()
        log_audit_event(
            self.db,
            actor="SAARTHI_AGENT",
            action="UPDATE_CASE",
            case_id=inp.case_id,
            input_payload=inp.model_dump(),
            output_payload={"case_id": inp.case_id, "status": inp.status, "outcome": inp.outcome}
        )
        return ToolExecutionResult(success=True, data={"case_id": inp.case_id, "status": inp.status})

    async def _escalate_to_human(self, inp: EscalateToHumanInput, case_id: Optional[str]) -> ToolExecutionResult:
        cid = inp.case_id or case_id
        case = self.db.query(Case).filter(Case.id == cid).first()
        if case:
            case.status = "ESCALATED"
            case.outcome = "HUMAN_ESCALATED"
            case.resolution_notes = inp.reason
            self.db.commit()

        log_audit_event(
            self.db,
            actor="SAARTHI_AGENT",
            action="ESCALATE_TO_HUMAN",
            case_id=cid,
            input_payload=inp.model_dump(),
            decision_reason=inp.reason,
            policy_citations=inp.policy_citations
        )
        return ToolExecutionResult(success=True, data={"case_id": cid, "escalated": True, "reason": inp.reason})

    async def _send_customer_update(self, inp: SendCustomerUpdateInput, case_id: Optional[str]) -> ToolExecutionResult:
        log_audit_event(
            self.db,
            actor="SAARTHI_AGENT",
            action="SEND_CUSTOMER_UPDATE",
            case_id=inp.case_id or case_id,
            input_payload=inp.model_dump(),
            output_payload={"delivered": True}
        )
        return ToolExecutionResult(success=True, data={"delivered": True, "status_chip": inp.status_chip})

