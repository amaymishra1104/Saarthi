# Policy POL-LMT-006: Autonomous Action Limits & Authorization Tiers

## Summary
Defines value thresholds and supervisory gates governing autonomous system actions versus human authorization.

## Policy Rules
1. **Rule LMT-1: Threshold Tiers**
   - **Tier 1 (Autonomous Resolution): Amount <= INR 5,000.00**
     The automated agent is permitted to execute reversals autonomously, subject to Permission Gate checks and verification.
   - **Tier 2 (Supervisor Approval Required): INR 5,000.01 to INR 50,000.00**
     The agent must pause execution, classify the case as `REQUIRE_APPROVAL`, generate a Case Brief, and place the case into the Human Agent Console. The human supervisor may approve or reject. Upon approval, the agent executes and verifies.
   - **Tier 3 (Manual Operations Only): Amount > INR 50,000.00**
     Directly routed for specialized manual handling; no automated execution allowed even with standard supervisor click-through.

2. **Rule LMT-2: Velocity and Frequency Limits**
   A maximum of 1 autonomous reversal per customer identifier per rolling 24-hour window. Subsequent claims within 24 hours require human review.

