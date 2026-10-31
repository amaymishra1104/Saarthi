# Policy POL-PSH-002: Pending Status & Unconfirmed Transactions

## Summary
Mandates strict handling of ambiguous, processing, or pending transactions to prevent double debits and premature financial actions.

## Policy Rules
1. **Rule PSH-1: Absolute Prohibition of Status Inference**
   Neither the LLM nor any automated component is permitted to infer, predict, or guess the final status of a transaction marked `PENDING_CONFIRMATION`, `PROCESSING`, or having an unverified status source. The transaction must be treated strictly as `UNCONFIRMED`.

2. **Rule PSH-2: Customer Communication Constraint**
   When a transaction is in `PENDING_CONFIRMATION`, the customer response MUST explicitly state: "I can't call it failed or successful yet." No promise of immediate reversal may be made while the payment rail is still processing the settlement.

3. **Rule PSH-3: Case Tracking & Status-Change Notification**
   The agent must:
   - Create a tracked case in the internal ledger.
   - Set the case state to `AWAITING_STATUS_CHANGE`.
   - Escalate to the human operations queue with a structured Case Brief.
   - Promise the customer an automated update within 24 hours once the authoritative banking clearing signal is received.

4. **Rule PSH-4: Prohibition of Financial Actions**
   No financial write action (reversal, refund, or chargeback) may be initiated on any transaction whose status is `PENDING_CONFIRMATION`.

