# Policy POL-ESC-005: Escalation & Risk Control Rules

## Summary
Specifies mandatory escalation conditions, risk flags that halt automated execution, and Case Brief standards for human agents.

## Policy Rules
1. **Rule ESC-1: Mandatory Escalation Triggers**
   Autonomous resolution must immediately halt and escalate to a human agent when:
   - Transaction status lookup fails, returns 404, or customer identity cannot be verified.
   - Status is ambiguous (`PENDING_CONFIRMATION` or unverified upstream clearing).
   - Any active risk flag is present on the transaction.
   - Permission Gate returns `DENY` or `REQUIRE_APPROVAL`.
   - Post-action verification fails (re-checked state does not match expected result).
   - Core API times out after bounded retry limit (max 2 retries with state check).

2. **Rule ESC-2: Strict Risk Flag Halting**
   If `risk_flags` contains values such as `FRAUD_SUSPECTED`, `VELOCITY_BREACH`, `ACCOUNT_DORMANT`, or `MERCHANT_BLACKLISTED`:
   - No automated financial or operational actions are permitted.
   - The case is immediately routed to the Risk & Security Operations queue.

3. **Rule ESC-3: Structured Case Brief Requirement**
   Every escalation must produce a structured Case Brief including:
   - Original customer complaint
   - Masked customer and transaction identifiers (e.g. `CUST-***492`, `TXN-***812`)
   - Verified transaction state and status source
   - Chronological list of actions attempted and results observed
   - List of policies consulted with specific rule citations
   - Concrete reason for escalation
   - Recommended next step ONLY if supported by confirmed factual evidence

