import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException
from .models import MockTransaction, ReversalResponse, ChaosConfig
from .seed_data import get_initial_transactions

class MockPaymentsService:
    def __init__(self):
        self._transactions: Dict[str, MockTransaction] = get_initial_transactions()
        self._idempotency_store: Dict[str, dict] = {}
        self._cases: Dict[str, dict] = {}
        self.chaos = ChaosConfig()

    def reset(self):
        """Reset mock bank state and chaos settings to pristine seed data."""
        self._transactions = get_initial_transactions()
        self._idempotency_store = {}
        self._cases = {}
        self.chaos = ChaosConfig()

    def set_chaos(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.chaos, k):
                setattr(self.chaos, k, bool(v))

    async def _simulate_latency(self):
        if self.chaos.api_timeout:
            # Simulate a severe gateway timeout (e.g. 5 seconds or exception)
            await asyncio.sleep(0.5)
            raise HTTPException(status_code=504, detail="Gateway Timeout: Upstream Banking Switch did not respond.")
        await asyncio.sleep(0.01)

    async def get_transaction(self, txn_id: str) -> MockTransaction:
        await self._simulate_latency()
        if self.chaos.lookup_fail:
            raise HTTPException(status_code=500, detail="Core Switch Error: Account lookup service unavailable.")
        
        txn = self._transactions.get(txn_id)
        if not txn:
            raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found in Payments Core.")
        
        # Ambiguous status chaos
        if self.chaos.ambiguous_status:
            copy = txn.model_copy()
            copy.status = "PENDING_CONFIRMATION"
            copy.status_source = "UNVERIFIED_GATEWAY"
            return copy

        return txn

    async def search_transactions(
        self,
        customer_id: Optional[str] = None,
        amount: Optional[float] = None,
        date: Optional[str] = None
    ) -> List[MockTransaction]:
        await self._simulate_latency()
        if self.chaos.lookup_fail:
            raise HTTPException(status_code=500, detail="Core Switch Error: Search service unavailable.")

        results = list(self._transactions.values())
        if customer_id:
            results = [t for t in results if t.customer_id.lower() == customer_id.lower()]
        if amount is not None:
            # Match within ₹5 buffer for fee variances
            results = [t for t in results if abs(t.amount - amount) < 1.0]
        if date:
            results = [t for t in results if t.timestamp.strftime("%Y-%m-%d") == date]
        
        return results

    async def check_transaction_status(self, txn_id: str) -> dict:
        txn = await self.get_transaction(txn_id)
        return {
            "txn_id": txn.txn_id,
            "status": txn.status,
            "status_source": txn.status_source,
            "debit_confirmed": txn.debit_confirmed,
            "credit_confirmed": txn.credit_confirmed,
            "risk_flags": txn.risk_flags,
            "reversal_eligible": txn.reversal_eligible,
            "reversal_ref": txn.reversal_ref,
            "amount": txn.amount,
            "merchant": txn.merchant,
            "timestamp": txn.timestamp.isoformat()
        }

    async def initiate_reversal(
        self,
        txn_id: str,
        idempotency_key: str,
        reason: str,
        requested_by: str = "SAARTHI_AGENT"
    ) -> ReversalResponse:
        await self._simulate_latency()

        if not idempotency_key:
            raise HTTPException(status_code=400, detail="Idempotency-Key header is strictly required.")

        # Check idempotency cache in payments core
        if idempotency_key in self._idempotency_store:
            cached = self._idempotency_store[idempotency_key]
            # Return identical previous response (Idempotent guarantee)
            return ReversalResponse(**cached)

        txn = self._transactions.get(txn_id)
        if not txn:
            raise HTTPException(status_code=404, detail=f"Transaction {txn_id} not found.")

        # Reversal is only valid for FAILED or DUPLICATE_DEBIT where debit is confirmed and credit is not
        valid_statuses = ("FAILED", "DUPLICATE_DEBIT")
        if txn.status not in valid_statuses:
            raise HTTPException(
                status_code=409,
                detail=f"Reversal rejected by Core: Status is '{txn.status}'. Only confirmed {valid_statuses} can be reversed."
            )

        if not txn.debit_confirmed:
            raise HTTPException(status_code=409, detail="Reversal rejected: Customer debit was never confirmed.")

        if txn.credit_confirmed:
            raise HTTPException(status_code=409, detail="Reversal rejected: Merchant credit was confirmed.")

        if txn.risk_flags:
            raise HTTPException(status_code=403, detail=f"Reversal rejected: Active risk flags detected: {txn.risk_flags}")

        # Generate settlement reference
        reversal_ref = f"REV-{uuid.uuid4().hex[:8].upper()}"

        # If verification mismatch chaos is active:
        # We return success from API, but we DO NOT update the transaction status to REVERSED in core!
        if self.chaos.verification_mismatch or txn_id == "TXN-1006":
            # API returns success, but internal state remains FAILED or MISMATCH
            # This triggers the agent's post-action state recheck failure!
            resp = ReversalResponse(
                success=True,
                txn_id=txn.txn_id,
                reversal_ref=reversal_ref,
                status="REVERSAL_INITIATED",
                message="Reversal order received by acquirer clearing queue.",
                timestamp=datetime.utcnow()
            )
            self._idempotency_store[idempotency_key] = resp.model_dump()
            return resp

        # Normal successful path: update core transaction state
        txn.status = "REVERSED"
        txn.status_source = "CORE_SWITCH"
        txn.reversal_ref = reversal_ref
        txn.reversal_eligible = False

        resp = ReversalResponse(
            success=True,
            txn_id=txn.txn_id,
            reversal_ref=reversal_ref,
            status="REVERSED",
            message=f"Reversal executed successfully. Funds credited to source via {reversal_ref}.",
            timestamp=datetime.utcnow()
        )
        self._idempotency_store[idempotency_key] = resp.model_dump()
        return resp

    async def create_case(self, case_data: dict) -> dict:
        await self._simulate_latency()
        case_id = case_data.get("case_id") or f"CASE-{uuid.uuid4().hex[:6].upper()}"
        case_data["case_id"] = case_id
        case_data["created_at"] = datetime.utcnow().isoformat()
        self._cases[case_id] = case_data
        return case_data

    async def update_case(self, case_id: str, updates: dict) -> dict:
        await self._simulate_latency()
        if case_id not in self._cases:
            self._cases[case_id] = {"case_id": case_id}
        self._cases[case_id].update(updates)
        self._cases[case_id]["updated_at"] = datetime.utcnow().isoformat()
        return self._cases[case_id]

# Singleton instance
mock_payments_service = MockPaymentsService()

