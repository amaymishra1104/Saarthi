# Policy POL-DUP-003: Duplicate Debit Handling Rules

## Summary
Governs resolution when a customer reports multiple debits for a single transaction or when core records identify a duplicate debit event.

## Policy Rules
1. **Rule DUP-1: Identification of Duplicate Debit**
   A duplicate debit condition occurs when:
   - The transaction status is explicitly marked `DUPLICATE_DEBIT`, OR
   - Two debits match identical customer, merchant, and amount within a 5-minute window, and only one merchant credit was fulfilled.

2. **Rule DUP-2: Permitted Remediation for Secondary Debit**
   The primary transaction must remain preserved. Only the secondary duplicate debit entry is eligible for reversal.
   - If amount <= INR 5,000.00 and no risk flags are present, autonomous reversal of the duplicate entry is permitted.
   - If amount > INR 5,000.00, the action requires supervisor approval via the Human Agent Console.
   - Idempotency key must reference the specific duplicate transaction reference (`REV-DUP-{txn_id}`).

3. **Rule DUP-3: Post-Action Verification**
   Verification must confirm the duplicate entry is marked `REVERSED` while the original legitimate transaction remains intact.

