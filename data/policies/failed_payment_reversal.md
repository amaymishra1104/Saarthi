# Policy POL-FPR-001: Failed Payment Reversal Rules

## Summary
Governs autonomous and human-assisted reversal of customer debits where the merchant transaction resulted in a confirmed failure.

## Policy Rules
1. **Rule FPR-1: Eligibility for Reversal**
   A transaction is eligible for an automated reversal if and only if all the following conditions are simultaneously met:
   - The authoritative transaction status in Payments Core is strictly `FAILED`.
   - The customer debit is confirmed (`debit_confirmed == True`).
   - The merchant credit is NOT confirmed (`credit_confirmed == False`).
   - The transaction flag `reversal_eligible` is `True`.
   - The transaction amount is less than or equal to the auto-action limit (INR 5,000.00).
   - There are zero risk flags on the transaction or customer account.

2. **Rule FPR-2: Deterministic Permission Gate Enforcement**
   Under no circumstances shall the language model (LLM) directly initiate a reversal. All reversal proposals must be validated by the deterministic Python Permission Gate. If the gate rejects the proposal, the action must be aborted and escalated.

3. **Rule FPR-3: Post-Action Verification Mandate**
   An initiated reversal is NOT assumed to have succeeded. A case may only be transitioned to `Resolved` status after an authoritative post-action state check returns `REVERSED` or `REVERSAL_PENDING` with a valid Bank Reference Number (RRN/UTR). If the state re-check shows no change, the system must report a verification mismatch and escalate.

4. **Rule FPR-4: Idempotency Enforcement**
   Every reversal request must carry a unique, deterministic idempotency key formatted as `REV-{txn_id}-{action_hash}`. The database must reject duplicate reversal requests on the same transaction.

