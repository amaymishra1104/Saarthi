from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# 1. lookup_transaction
class LookupTransactionInput(BaseModel):
    txn_id: Optional[str] = Field(None, description="Exact Transaction ID, e.g. 'TXN-1001'")
    customer_id: Optional[str] = Field(None, description="Customer Identifier, e.g. 'CUST-4921'")
    amount: Optional[float] = Field(None, description="Transaction amount in INR")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")

# 2. check_transaction_status
class CheckTransactionStatusInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID to verify authoritatively with Payments Core")

# 3. retrieve_policy
class RetrievePolicyInput(BaseModel):
    query: str = Field(..., description="Policy question or topic (e.g. 'reversal for failed payment', 'pending status rule', 'limits')")
    top_k: int = Field(3, description="Number of policy excerpts to retrieve")

# 4. get_permitted_actions
class GetPermittedActionsInput(BaseModel):
    status: str = Field(..., description="Confirmed transaction status, e.g. 'FAILED', 'PENDING_CONFIRMATION', 'DUPLICATE_DEBIT'")
    debit_confirmed: bool = Field(..., description="Whether debit from customer account is confirmed")
    credit_confirmed: bool = Field(..., description="Whether credit to merchant account is confirmed")

# 5. initiate_reversal
class InitiateReversalInput(BaseModel):
    txn_id: str = Field(..., description="Transaction ID to reverse")
    reason: str = Field(..., description="Reason for reversal citing policy rule")
    idempotency_key: str = Field(..., description="Unique deterministic idempotency key, e.g. 'REV-TXN-1001'")

# 6. create_case
class CreateCaseInput(BaseModel):
    customer_id: str = Field(..., description="Customer ID")
    complaint_text: str = Field(..., description="Original customer complaint")
    txn_id: Optional[str] = Field(None, description="Associated transaction ID if known")

# 7. update_case
class UpdateCaseInput(BaseModel):
    case_id: str = Field(..., description="Case ID to update")
    status: str = Field(..., description="New status (e.g. 'INVESTIGATING', 'RESOLVED', 'ESCALATED', 'AWAITING_STATUS_CHANGE')")
    outcome: Optional[str] = Field(None, description="Final outcome code")
    resolution_notes: Optional[str] = Field(None, description="Resolution summary or update details")

# 8. escalate_to_human
class EscalateToHumanInput(BaseModel):
    case_id: str = Field(..., description="Case ID to escalate")
    reason: str = Field(..., description="Detailed rationale for human escalation")
    policy_citations: List[str] = Field(default_factory=list, description="Policy rules cited")
    recommended_next_step: Optional[str] = Field(None, description="Factual recommendation for human agent")

# 9. send_customer_update
class SendCustomerUpdateInput(BaseModel):
    case_id: str = Field(..., description="Case ID")
    message: str = Field(..., description="Customer-facing message")
    status_chip: str = Field(..., description="Status badge: 'INVESTIGATING', 'RESOLVED_VERIFIED', 'ESCALATED', 'AWAITING_STATUS_CHANGE'")
    language: str = Field("en", description="Target customer language ('en', 'hi', 'hinglish')")

# Tool Registry Metadata for LLM tool calling
APPROVED_TOOLS_METADATA = [
    {
        "name": "lookup_transaction",
        "description": "Lookup transaction details from Payments Core using transaction ID, customer ID, amount, or date.",
        "parameters": LookupTransactionInput.model_json_schema()
    },
    {
        "name": "check_transaction_status",
        "description": "Authoritatively check the current state of a transaction in Payments Core. Never infer or guess status.",
        "parameters": CheckTransactionStatusInput.model_json_schema()
    },
    {
        "name": "retrieve_policy",
        "description": "Retrieve governing business and compliance policy rules with citations.",
        "parameters": RetrievePolicyInput.model_json_schema()
    },
    {
        "name": "get_permitted_actions",
        "description": "Query the rule engine for actions legally permitted for a given confirmed transaction state.",
        "parameters": GetPermittedActionsInput.model_json_schema()
    },
    {
        "name": "initiate_reversal",
        "description": "Trigger a financial reversal. Note: Application Permission Gate will deterministically validate this call before execution.",
        "parameters": InitiateReversalInput.model_json_schema()
    },
    {
        "name": "create_case",
        "description": "Create a tracked case record in the Saarthi dispute ledger.",
        "parameters": CreateCaseInput.model_json_schema()
    },
    {
        "name": "update_case",
        "description": "Update the state, outcome, or notes of an existing case.",
        "parameters": UpdateCaseInput.model_json_schema()
    },
    {
        "name": "escalate_to_human",
        "description": "Escalate the case to human operations when state is ambiguous, risk is flagged, limits exceeded, or approval required.",
        "parameters": EscalateToHumanInput.model_json_schema()
    },
    {
        "name": "send_customer_update",
        "description": "Send an update or final verified resolution message to the customer.",
        "parameters": SendCustomerUpdateInput.model_json_schema()
    }
]

