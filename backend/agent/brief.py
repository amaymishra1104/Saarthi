import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from backend.db.audit import mask_pii_string, mask_pii_data

class CaseBrief(BaseModel):
    case_id: str
    generated_at: str
    original_issue: str
    transaction_info: Dict[str, Any]
    actions_attempted: List[str]
    results_observed: List[str]
    checks_performed: List[str]
    policies_consulted: List[str]
    reason_for_escalation: str
    recommended_next_step: Optional[str] = None

    def to_markdown(self) -> str:
        lines = [
            f"# 📋 Case Brief: {self.case_id}",
            f"**Generated:** {self.generated_at} (UTC)",
            "",
            "### 1. Original Customer Complaint",
            f"> {self.original_issue}",
            "",
            "### 2. Transaction Information (PII-Masked)",
            f"- **Txn ID:** `{self.transaction_info.get('txn_id', 'N/A')}`",
            f"- **Amount:** `₹{self.transaction_info.get('amount', '0.00')}`",
            f"- **Merchant:** `{self.transaction_info.get('merchant', 'N/A')}`",
            f"- **Reported Status:** `{self.transaction_info.get('status', 'UNCONFIRMED')}`",
            f"- **Status Source:** `{self.transaction_info.get('status_source', 'N/A')}`",
            f"- **Customer ID:** `{mask_pii_string(str(self.transaction_info.get('customer_id', 'N/A')))}`",
            "",
            "### 3. Checks Performed by Saarthi",
        ]
        for c in self.checks_performed:
            lines.append(f"- [x] {c}")

        lines.extend(["", "### 4. Actions Attempted & Results"])
        if self.actions_attempted:
            for act, res in zip(self.actions_attempted, self.results_observed):
                lines.append(f"- **Attempted:** `{act}` → **Observed:** `{res}`")
        else:
            lines.append("- *No automated actions executed (halted at Permission Gate)*")

        lines.extend(["", "### 5. Policies Consulted & Citations"])
        for p in self.policies_consulted:
            lines.append(f"- {p}")

        lines.extend([
            "",
            "### 6. Escalation Rationale",
            f"**Reason:** {self.reason_for_escalation}",
            "",
            "### 7. Recommended Next Step",
            f"**Recommendation:** {self.recommended_next_step or 'Manual investigation required; no definitive automated recommendation.'}"
        ])
        return "\n".join(lines)

def build_case_brief(
    case_id: str,
    original_issue: str,
    transaction_info: Dict[str, Any],
    actions_attempted: List[str],
    results_observed: List[str],
    checks_performed: List[str],
    policies_consulted: List[str],
    reason_for_escalation: str,
    recommended_next_step: Optional[str] = None
) -> CaseBrief:
    safe_txn = mask_pii_data(transaction_info)
    return CaseBrief(
        case_id=case_id,
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        original_issue=mask_pii_string(original_issue),
        transaction_info=safe_txn,
        actions_attempted=actions_attempted,
        results_observed=results_observed,
        checks_performed=checks_performed,
        policies_consulted=policies_consulted,
        reason_for_escalation=reason_for_escalation,
        recommended_next_step=recommended_next_step
    )

