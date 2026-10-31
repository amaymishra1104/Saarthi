from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., description="Customer complaint or question")
    customer_id: str = Field("CUST-4921", description="Customer ID")
    case_id: Optional[str] = Field(None, description="Existing case ID if continuing conversation")

class StepTrace(BaseModel):
    step_name: str
    status: str
    state_data: Dict[str, Any]
    timestamp: str

class ChatResponse(BaseModel):
    case_id: Optional[str]
    status: str
    outcome: Optional[str]
    customer_message: str
    status_chip: str
    steps: List[Dict[str, Any]]
    case_brief: Optional[Dict[str, Any]] = None
    is_faq: bool = False

class SupervisorApprovalRequest(BaseModel):
    decision: str = Field(..., description="'APPROVE' or 'REJECT'")
    supervisor_id: str = Field("SUPV-OPS-01", description="Supervisor identifier")
    notes: Optional[str] = Field(None, description="Supervisor decision notes")

class SupervisorReplyRequest(BaseModel):
    message: str = Field(..., description="Direct message to customer from human agent")

class ChaosUpdateRequest(BaseModel):
    lookup_fail: Optional[bool] = None
    api_timeout: Optional[bool] = None
    ambiguous_status: Optional[bool] = None
    duplicate_attempt: Optional[bool] = None
    verification_mismatch: Optional[bool] = None

class ScenarioPreset(BaseModel):
    scenario_id: str
    title: str
    description: str
    customer_id: str
    txn_id: str
    amount: float
    merchant: str
    sample_prompt: str
    expected_outcome: str
    category: str

